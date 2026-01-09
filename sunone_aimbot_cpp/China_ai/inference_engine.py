"""
推理引擎模块

该模块包含TensorRT推理引擎的实现和相关辅助函数。
负责模型加载、转换和推理执行。
"""
import os
import time
import subprocess
import sys
import traceback


class TensorRTInferenceEngine:
    """
    TensorRT推理引擎

    用于加载和执行TensorRT engine模型进行推理。
    支持从onnx模型自动转换为TensorRT格式。
    """

    def __init__(self, engine_path):
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
        except (ImportError, OSError) as e:
            raise RuntimeError(
                f'未检测到TensorRT/CUDA环境，无法使用TensorRT加速。请安装相关依赖或切换到ONNX Runtime。原始错误: {e}')
        cuda.init()
        self.logger = trt.Logger(trt.Logger.INFO)
        self.device = cuda.Device(0)
        self.ctx = self.device.retain_primary_context()
        self.ctx.push()
        try:
            with open(engine_path, 'rb') as f:
                with trt.Runtime(self.logger) as runtime:
                    self.engine = runtime.deserialize_cuda_engine(f.read())
            if self.engine is None:
                os.remove(engine_path)
                onnx_path = os.path.splitext(engine_path)[0] + '.onnx'
                if not os.path.exists(onnx_path):
                    raise RuntimeError(f'找不到对应的onnx文件: {onnx_path}')
                import subprocess
                cmd = f'trtexec --onnx="{onnx_path}" --saveEngine="{engine_path}"'
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           encoding='utf-8')
                for line in process.stdout:
                    print(line, end='')
                process.wait()
                if process.returncode != 0:
                    self.ctx.pop()
                    raise RuntimeError('trtexec 重新生成engine失败，请检查日志！')
                with open(engine_path, 'rb') as f2:
                    with trt.Runtime(self.logger) as runtime2:
                        self.engine = runtime2.deserialize_cuda_engine(f2.read())
                if self.engine is None:
                    self.ctx.pop()
                    raise RuntimeError('TensorRT engine 加载失败，请确认onnx模型和环境！')
            self.context = self.engine.create_execution_context()
            self.inputs, self.outputs, self.bindings, self.stream = self.allocate_buffers()
            try:
                import cupy
                import cupy.cuda.graph as cuda_graph
                cuda_version = cuda.get_version()
                try:
                    cupy.cuda.Device(0).use()
                except Exception:
                    pass
                self._graph_supported = True
                self._use_cupy_graph = True
                try:
                    self._cupy_stream = cupy.cuda.Stream(non_blocking=True)
                except Exception:
                    self._cupy_stream = None
            except ImportError:
                self._graph_supported = False
                self._use_cupy_graph = False
                self._cupy_stream = None
            self._use_cuda_graph = False
            self._graph_exec = None
            self._graph = None
            self._graph_warmed = False
        except Exception as e:
            self.ctx.pop()
            raise e

    def enable_cuda_graph(self, force=False):
        """
        手动启用 CUDA Graph 功能

        Args:
            force (bool): 强制启用，即使检测到兼容性问题
        """
        try:
            import cupy
            import pycuda.driver as cuda
            cuda.init()
            cuda_version = cuda.get_version()
            if cuda_version >= (10, 0) or force:
                self._graph_supported = True
                self._use_cuda_graph = True
                self._use_cupy_graph = True
                if getattr(self, '_cupy_stream', None) is None:
                    self._cupy_stream = cupy.cuda.Stream(non_blocking=True)
                return True
            print(f'CUDA 版本过低 ({cuda_version}，需要 10.0+)')
            return False
        except ImportError:
            print('CuPy 或 PyCUDA 未安装，无法启用 CUDA Graph')
            return False
        except Exception as e:
            print(f'启用 CUDA Graph 失败: {e}')
            return False

    def disable_cuda_graph(self):
        """禁用 CUDA Graph 功能"""
        self._graph_supported = False
        self._use_cuda_graph = False
        self._use_cupy_graph = False
        self._graph = None
        self._graph_exec = None
        print('CUDA Graph 已禁用')

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        """显式清理CUDA资源"""
        if hasattr(self, '_graph') and self._graph is not None:
            try:
                self._graph = None
            except Exception:
                pass
        if hasattr(self, '_cupy_stream') and self._cupy_stream is not None:
            try:
                self._cupy_stream.synchronize()
            except Exception:
                pass
        if hasattr(self, '_graph_exec') and self._graph_exec is not None:
            try:
                self._graph_exec = None
            except Exception:
                pass
        if hasattr(self, 'ctx'):
            try:
                import pycuda.driver as cuda
                current = None
                try:
                    current = cuda.Context.get_current()
                except cuda.LogicError:
                    pass
                if current is not None and current.handle == self.ctx.handle:
                    self.ctx.pop()
                else:
                    pass
            except Exception as e:
                print(f'清理CUDA上下文时出错: {e}')
            finally:
                if hasattr(self, 'ctx'):
                    delattr(self, 'ctx')

    def allocate_buffers(self):
        """
        为模型输入输出分配CUDA内存

        Returns:
            tuple: 包含输入、输出、绑定和CUDA流的元组
        """
        import pycuda.driver as cuda
        import tensorrt as trt
        inputs = []
        outputs = []
        bindings = []
        stream = cuda.Stream()
        for binding in self.engine:
            shape = self.engine.get_tensor_shape(binding)
            size = trt.volume(shape)
            dtype = trt.nptype(self.engine.get_tensor_dtype(binding))
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            bindings.append(int(device_mem))
            if self.engine.get_tensor_mode(binding) == trt.TensorIOMode.INPUT:
                inputs.append({'host': host_mem, 'device': device_mem})
            else:
                outputs.append({'host': host_mem, 'device': device_mem})
        return (inputs, outputs, bindings, stream)

    def infer(self, input_array):
        """
        执行模型推理

        Args:
            input_array: 输入数据数组

        Returns:
            list: 推理结果
        """
        import pycuda.driver as cuda
        import numpy as np
        use_graph = bool(
            getattr(self, '_use_cuda_graph', False) and getattr(self, '_graph_supported', False) and getattr(self,
                                                                                                             '_use_cupy_graph',
                                                                                                             False) and (
                        self._cupy_stream is not None))
        self.ctx.push()
        try:
            np.copyto(self.inputs[0]['host'], input_array.ravel())
            if use_graph:
                import cupy
                import cupy.cuda.runtime as rt
                try:
                    stream = self._cupy_stream
                    if self._graph is None:
                        stream.synchronize()
                        rt.memcpyAsync(int(self.inputs[0]['device']), self.inputs[0]['host'].ctypes.data,
                                       self.inputs[0]['host'].nbytes, 1, stream.ptr)
                        try:
                            input_binding = self.engine[0]
                            output_binding = self.engine[1]
                            self.context.set_tensor_address(input_binding, int(self.inputs[0]['device']))
                            self.context.set_tensor_address(output_binding, int(self.outputs[0]['device']))
                            self.context.execute_async_v3(stream_handle=int(stream.ptr))
                        except AttributeError:
                            self.context.set_binding_address(0, int(self.inputs[0]['device']))
                            self.context.set_binding_address(1, int(self.outputs[0]['device']))
                            self.context.execute_async_v2(bindings=self.bindings, stream_handle=int(stream.ptr))
                        rt.memcpyAsync(self.outputs[0]['host'].ctypes.data, int(self.outputs[0]['device']),
                                       self.outputs[0]['host'].nbytes, 2, stream.ptr)
                        stream.synchronize()
                        self._graph_warmed = True
                        try:
                            stream.begin_capture(mode=cupy.cuda.graph.CaptureMode.RELAXED)
                        except Exception:
                            stream.begin_capture()
                        rt.memcpyAsync(int(self.inputs[0]['device']), self.inputs[0]['host'].ctypes.data,
                                       self.inputs[0]['host'].nbytes, 1, stream.ptr)
                        try:
                            input_binding = self.engine[0]
                            output_binding = self.engine[1]
                            self.context.set_tensor_address(input_binding, int(self.inputs[0]['device']))
                            self.context.set_tensor_address(output_binding, int(self.outputs[0]['device']))
                            self.context.execute_async_v3(stream_handle=int(stream.ptr))
                        except AttributeError:
                            self.context.set_binding_address(0, int(self.inputs[0]['device']))
                            self.context.set_binding_address(1, int(self.outputs[0]['device']))
                            self.context.execute_async_v2(bindings=self.bindings, stream_handle=int(stream.ptr))
                        rt.memcpyAsync(self.outputs[0]['host'].ctypes.data, int(self.outputs[0]['device']),
                                       self.outputs[0]['host'].nbytes, 2, stream.ptr)
                        self._graph = stream.end_capture()
                        self._graph.launch(stream)
                        stream.synchronize()
                        return [self.outputs[0]['host']]
                    self._graph.launch(stream)
                    stream.synchronize()
                    return [self.outputs[0]['host']]
                except Exception as e:
                    print(f'[TRT] CUDA Graph 捕获失败，回退常规路径: {e}')
                    self._use_cuda_graph = False
                    self._graph_supported = False
            cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
            try:
                input_binding = self.engine[0]
                output_binding = self.engine[1]
                self.context.set_tensor_address(input_binding, int(self.inputs[0]['device']))
                self.context.set_tensor_address(output_binding, int(self.outputs[0]['device']))
                self.context.execute_async_v3(stream_handle=int(self.stream.handle))
            except AttributeError:
                self.context.set_binding_address(0, int(self.inputs[0]['device']))
                self.context.set_binding_address(1, int(self.outputs[0]['device']))
                self.context.execute_async_v2(bindings=self.bindings, stream_handle=int(self.stream.handle))
            cuda.memcpy_dtoh_async(self.outputs[0]['host'], self.outputs[0]['device'], self.stream)
            self.stream.synchronize()
            return [self.outputs[0]['host']]
        finally:
            self.ctx.pop()

    def get_input_shape(self):
        """获取模型输入形状"""
        binding = self.engine[0]
        return self.engine.get_tensor_shape(binding)

    def get_class_num(self):
        """获取模型分类数量"""
        binding = self.engine[1]
        return self.engine.get_tensor_shape(binding)[-1] - 5

    def get_class_num_v8(self):
        """获取YOLOv8模型分类数量"""
        binding = self.engine[1]
        return self.engine.get_tensor_shape(binding)[-1] - 4


def auto_convert_engine(model_path):
    """
    自动将ONNX模型转换为TensorRT引擎

    Args:
        model_path: ONNX模型路径

    Returns:
        bool: 转换是否成功
    """
    import subprocess
    import os
    import numpy as np
    print(f'开始TRT转换流程，模型路径: {model_path}')
    try:
        import tensorrt as trt
        import pycuda.driver as cuda
        import onnxruntime as ort
        print(f'TensorRT版本: {trt.__version__}')
        cuda.init()
        print('CUDA驱动初始化成功')
    except ImportError as e:
        print(f'TensorRT环境未安装: {e}')
        print('请安装以下组件：')
        print('1. CUDA Toolkit')
        print('2. cuDNN')
        print('3. TensorRT')
        print('4. PyCUDA')
        print('5. ONNX Runtime')
        return False
    base_path = os.path.splitext(model_path)[0]
    print(f'基础路径: {base_path}')
    if os.path.exists(base_path + '.onnx'):
        onnx_path = base_path + '.onnx'
        print(f'找到ONNX模型: {onnx_path}')
    elif os.path.exists(base_path + '.data'):
        onnx_path = base_path + '.data'
        print(f'找到DATA模型: {onnx_path}')
    else:
        print(f'未找到同名原始模型: {base_path}.onnx 或 {base_path}.data')
        return False
    try:
        print('开始验证模型文件...')
        providers = ['DmlExecutionProvider',
                     'CPUExecutionProvider'] if 'DmlExecutionProvider' in ort.get_available_providers() else [
            'CPUExecutionProvider']
        print(f'使用的推理提供程序: {providers}')
        sess = ort.InferenceSession(onnx_path, providers=providers)
        input_name = sess.get_inputs()[0].name
        input_shape = sess.get_inputs()[0].shape
        print(f'模型输入名: {input_name}, 输入shape: {input_shape}')
    except Exception as e:
        print(f'模型验证失败: {e}')
        return False
    engine_path = base_path + '.engine'
    print(f'目标引擎路径: {engine_path}')
    try:
        print('检测GPU FP16支持...')
        device = cuda.Device(0)
        ctx = device.make_context()
        try:
            major, minor = device.compute_capability()
            supports_fp16 = major > 6 or (major == 6 and minor >= 0)
            print(f'GPU计算能力: {major}.{minor}, FP16支持: {supports_fp16}')
        finally:
            ctx.pop()
    except Exception as e:
        print(f'检测FP16支持时出错: {e}')
        supports_fp16 = False
    cmd = f'trtexec --onnx="{onnx_path}" --saveEngine="{engine_path}" --verbose'
    if supports_fp16:
        cmd += ' --fp16'
        print('启用FP16精度优化')
    print(f'执行转换命令: {cmd}')
    print('开始执行trtexec转换...')
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8',
                               bufsize=1, universal_newlines=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f'[TRT输出] {output.strip()}')
    process.wait()
    print(f'trtexec进程返回码: {process.returncode}')
    if process.returncode != 0:
        print('trtexec 转换失败，请检查日志！')
        return False
    print('trtexec 转换完成！')
    print('验证生成的engine文件...')
    try:
        logger = trt.Logger(trt.Logger.INFO)
        with open(engine_path, 'rb') as f:
            with trt.Runtime(logger) as runtime:
                engine = runtime.deserialize_cuda_engine(f.read())
        print('engine文件反序列化成功')
        ctx = cuda.Device(0).make_context()
        try:
            print(f'engine张量数量: {engine.num_io_tensors}')
            for i in range(engine.num_io_tensors):
                name = engine.get_tensor_name(i)
                shape = engine.get_tensor_shape(name)
                print(f'engine tensor[{i}] name: {name}, shape: {shape}')
        finally:
            ctx.pop()
    except Exception as e:
        print(f'验证engine文件时出错: {e}')
        return False
    print('TRT转换流程完成')
    return True


def auto_convert_engine_from_memory(
    model_bytes,
    output_engine_path,
    target_hw=None,
    use_fp16=True,
    workspace_mb=1024,
    builder_optimization_level: int = 5,
):
    """
    从内存中的 ONNX 数据直接转换为 TensorRT 引擎（保持输出文件名不变）

    Args:
        model_bytes: bytes, 内存中的 ONNX 模型
        output_engine_path: 最终引擎文件路径（可带或不带 .engine）
        target_hw: (H, W)；为 None 则按模型/默认推断
        use_fp16: 如平台支持则启用 FP16
        workspace_mb: 构建最大工作空间（MB）
        builder_optimization_level: 0~5
    Returns:
        (success: bool, final_engine_path: str)
    """
    print("开始从内存转换TRT引擎")
    print(f"输出路径: {output_engine_path}")
    print(f"目标分辨率: {target_hw}")
    print(f"使用FP16: {use_fp16}")
    print(f"工作空间: {workspace_mb}MB")
    print(f"优化等级: {builder_optimization_level}")

    # ---- 依赖检查 ----
    try:
        import tensorrt as trt
        import pycuda.driver as cuda
        import onnxruntime as ort
        import numpy as np
        cuda.init()
        print(f"TensorRT版本: {trt.__version__}")
        print("CUDA驱动初始化成功")
    except ImportError as e:
        print(f"TensorRT环境未安装: {e}")
        print("请安装以下组件：\n1. CUDA Toolkit\n2. cuDNN\n3. TensorRT\n4. PyCUDA\n5. ONNX Runtime")
        return (False, output_engine_path)

    # ---- 最终输出路径规范化 ----
    base, ext = os.path.splitext(output_engine_path)
    final_engine_path = output_engine_path if ext else (output_engine_path + ".engine")
    print(f"最终引擎路径: {final_engine_path}")

    # ---- 轻量验证 ONNX & 推断输入尺寸 ----
    try:
        providers = (
            ["DmlExecutionProvider", "CPUExecutionProvider"]
            if "DmlExecutionProvider" in ort.get_available_providers()
            else ["CPUExecutionProvider"]
        )
        print(f"使用推理提供程序: {providers}")
        # onnxruntime 支持 bytes 作为模型输入（较新版本），失败则抛异常
        sess = ort.InferenceSession(model_bytes, providers=providers)
        input_name = sess.get_inputs()[0].name
        input_shape = sess.get_inputs()[0].shape
        print(f"ONNX 输入: name={input_name}, shape={input_shape}")
        del sess
    except Exception as e:
        print(f"模型验证失败: {e}")
        return (False, final_engine_path)

    # ---- 解析目标尺寸 ----
    if target_hw and len(target_hw) == 2:
        H_W = (int(target_hw[0]), int(target_hw[1]))
        print(f"使用指定的目标尺寸: {H_W}")
    else:
        try:
            h = int(input_shape[2]) if isinstance(input_shape[2], (int, np.integer)) else 640
            w = int(input_shape[3]) if isinstance(input_shape[3], (int, np.integer)) else 640
            H_W = (h, w)
            print(f"从ONNX推断目标尺寸: {H_W}")
        except Exception:
            H_W = (640, 640)
            print(f"使用默认目标尺寸: {H_W}")

    print(f"目标输入尺寸: {H_W[0]}x{H_W[1]}")

    # 已存在则复用
    if os.path.exists(final_engine_path):
        print(f"发现已存在引擎: {final_engine_path}")
        return (True, final_engine_path)

    # ---- 构建引擎 ----
    try:
        logger = trt.Logger(trt.Logger.INFO)
        builder = trt.Builder(logger)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, logger)

        print("解析ONNX模型...")
        if not parser.parse(model_bytes):
            print("ONNX模型解析失败:")
            for i in range(parser.num_errors):
                print(f"  错误 {i}: {parser.get_error(i)}")
            return (False, final_engine_path)

        print("创建构建配置...")
        config = builder.create_builder_config()

        # 工作空间
        workspace_bytes = int(workspace_mb) * 1024 * 1024
        print(f"设置工作空间: {workspace_bytes} 字节")
        try:
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_bytes)
            print("使用新API设置工作空间")
        except Exception:
            config.max_workspace_size = workspace_bytes
            print("使用旧API设置工作空间")

        # 优化等级
        try:
            config.builder_optimization_level = max(0, min(5, int(builder_optimization_level)))
            print(f"设置优化等级: {config.builder_optimization_level}")
        except Exception:
            print("无法设置优化等级")

        # FP16
        fp16_enabled = False
        if use_fp16 and getattr(builder, "platform_has_fast_fp16", False):
            try:
                config.set_flag(trt.BuilderFlag.FP16)
                fp16_enabled = True
                print("启用FP16")
            except Exception:
                print("无法启用FP16，继续使用FP32")
        else:
            print(
                f"FP16不可用或未启用 "
                f"(use_fp16={use_fp16}, platform_has_fast_fp16={getattr(builder, 'platform_has_fast_fp16', False)})"
            )

        # 处理输入维度 / 动态 profile
        input_tensor = network.get_input(0)
        dims = list(input_tensor.shape)
        print(f"输入张量维度: {dims}")

        has_dynamic = any(d is None or (isinstance(d, int) and d < 0) for d in dims)
        if has_dynamic:
            print("为动态输入创建优化Profile (固定为目标尺寸)")
            profile = builder.create_optimization_profile()
            min_shape = (1, 3, H_W[0], H_W[1])
            opt_shape = (1, 3, H_W[0], H_W[1])
            max_shape = (1, 3, H_W[0], H_W[1])
            print(f"Profile形状 - min: {min_shape}, opt: {opt_shape}, max: {max_shape}")
            try:
                profile.set_shape(input_tensor.name, min=min_shape, opt=opt_shape, max=max_shape)
                print("使用新API设置形状")
            except TypeError:
                profile.set_shape(input_tensor.name, min_shape, opt_shape, max_shape)
                print("使用旧API设置形状")
            config.add_optimization_profile(profile)
            print("添加优化Profile成功")
        else:
            if (dims[2], dims[3]) != H_W:
                try:
                    print(f"调整静态输入shape {dims} -> [1,3,{H_W[0]},{H_W[1]}]")
                    input_tensor.shape = (1, 3, H_W[0], H_W[1])
                except Exception as e:
                    print(f"静态shape调整失败: {e}")

        print("开始构建引擎…")
        engine_bytes = builder.build_serialized_network(network, config)
        if not engine_bytes:
            print("TensorRT引擎构建失败")
            return (False, final_engine_path)

        # 写文件
        os.makedirs(os.path.dirname(final_engine_path) or ".", exist_ok=True)
        with open(final_engine_path, "wb") as f:
            f.write(engine_bytes)
        print(f"已保存: {final_engine_path}")

        # 反序列化验证
        with open(final_engine_path, "rb") as f:
            runtime = trt.Runtime(logger)
            engine = runtime.deserialize_cuda_engine(f.read())
            if engine is None:
                print("引擎反序列化失败")
                return (False, final_engine_path)
            print(f"引擎IO张量数量: {engine.num_io_tensors}")

        print("内存转换流程完成")
        return (True, final_engine_path)

    except Exception as e:
        print(f"TensorRT引擎转换失败: {e}")
        traceback.print_exc()
        try:
            if os.path.exists(final_engine_path):
                os.remove(final_engine_path)
                print(f"已删除不完整引擎: {final_engine_path}")
        except Exception:
            pass
        return (False, final_engine_path)



def ensure_engine_from_memory(model_bytes, base_output_engine_path, target_hw, use_fp16=True, workspace_mb=1024,
                              builder_optimization_level: int = 5):
    """
    若指定分辨率的engine不存在则从内存构建，返回最终engine路径。

    Args:
        model_bytes: 内存ONNX字节
        base_output_engine_path: 基础输出路径（不含 _HxW 后缀或随意，函数会追加）
        target_hw: (H, W)
    Returns:
        final_engine_path: 构建或复用的engine路径（字符串）；失败时返回基础路径（便于上层处理）
    """
    ok, final_path = auto_convert_engine_from_memory(model_bytes=model_bytes,
                                                     output_engine_path=base_output_engine_path, target_hw=target_hw,
                                                     use_fp16=use_fp16, workspace_mb=workspace_mb,
                                                     builder_optimization_level=builder_optimization_level)
    return final_path
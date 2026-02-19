// cuda_12_8_fused_preprocess.cu
#include <cuda_runtime.h>
#include <stdint.h>
#include <math.h>

struct ResizeParams {
    int in_w;
    int in_h;
    int out_w;
    int out_h;
    float scale_x;
    float scale_y;
    float mean[3];
    float std_[3];
};

__device__ __forceinline__ float3 load_bgr_as_rgb(
    const unsigned char* __restrict__ src,
    int pitch_bytes,
    int x,
    int y)
{
    const unsigned char* p = src + y * pitch_bytes + x * 3;
    return make_float3(static_cast<float>(p[2]), static_cast<float>(p[1]), static_cast<float>(p[0]));
}

__device__ __forceinline__ float3 sample_bilinear_bgr_to_rgb(
    const unsigned char* __restrict__ src,
    int sw, int sh, int pitch_bytes,
    float x, float y)
{
    x = fminf(fmaxf(x, 0.0f), static_cast<float>(sw - 1));
    y = fminf(fmaxf(y, 0.0f), static_cast<float>(sh - 1));

    int x0 = static_cast<int>(floorf(x));
    int y0 = static_cast<int>(floorf(y));
    int x1 = min(x0 + 1, sw - 1);
    int y1 = min(y0 + 1, sh - 1);

    float dx = x - static_cast<float>(x0);
    float dy = y - static_cast<float>(y0);

    float3 c00 = load_bgr_as_rgb(src, pitch_bytes, x0, y0);
    float3 c01 = load_bgr_as_rgb(src, pitch_bytes, x1, y0);
    float3 c10 = load_bgr_as_rgb(src, pitch_bytes, x0, y1);
    float3 c11 = load_bgr_as_rgb(src, pitch_bytes, x1, y1);

    float3 f0 = make_float3(
        c00.x + (c01.x - c00.x) * dx,
        c00.y + (c01.y - c00.y) * dx,
        c00.z + (c01.z - c00.z) * dx);
    float3 f1 = make_float3(
        c10.x + (c11.x - c10.x) * dx,
        c10.y + (c11.y - c10.y) * dx,
        c10.z + (c11.z - c10.z) * dx);

    return make_float3(
        f0.x + (f1.x - f0.x) * dy,
        f0.y + (f1.y - f0.y) * dy,
        f0.z + (f1.z - f0.z) * dy);
}

__global__ void fused_preprocess_kernel_bgr8_to_nchw32f(
    const unsigned char* __restrict__ src,
    int sw, int sh, int src_pitch_bytes,
    float* __restrict__ dst,
    ResizeParams params)
{
    int ox = blockIdx.x * blockDim.x + threadIdx.x;
    int oy = blockIdx.y * blockDim.y + threadIdx.y;
    if (ox >= params.out_w || oy >= params.out_h) return;

    int out_idx = oy * params.out_w + ox;

    float ix = (static_cast<float>(ox) + 0.5f) * params.scale_x - 0.5f;
    float iy = (static_cast<float>(oy) + 0.5f) * params.scale_y - 0.5f;

    float3 rgb = sample_bilinear_bgr_to_rgb(src, sw, sh, src_pitch_bytes, ix, iy);

    rgb.x *= (1.0f / 255.0f);
    rgb.y *= (1.0f / 255.0f);
    rgb.z *= (1.0f / 255.0f);

    rgb.x = (rgb.x - params.mean[0]) / params.std_[0];
    rgb.y = (rgb.y - params.mean[1]) / params.std_[1];
    rgb.z = (rgb.z - params.mean[2]) / params.std_[2];

    const int plane = params.out_w * params.out_h;
    dst[out_idx] = rgb.x;
    dst[plane + out_idx] = rgb.y;
    dst[plane * 2 + out_idx] = rgb.z;
}

extern "C" void launch_fused_preprocess(
    const unsigned char* d_bgr, int in_w, int in_h, int src_pitch_bytes,
    float* d_out, int out_w, int out_h,
    const float mean[3], const float std_[3],
    cudaStream_t stream)
{
    ResizeParams params{};
    params.in_w = in_w;
    params.in_h = in_h;
    params.out_w = out_w;
    params.out_h = out_h;
    params.scale_x = static_cast<float>(in_w) / static_cast<float>(out_w);
    params.scale_y = static_cast<float>(in_h) / static_cast<float>(out_h);
    params.mean[0] = mean[0]; params.mean[1] = mean[1]; params.mean[2] = mean[2];
    params.std_[0] = std_[0]; params.std_[1] = std_[1]; params.std_[2] = std_[2];

    dim3 block(32, 16);
    dim3 grid((out_w + block.x - 1) / block.x,
        (out_h + block.y - 1) / block.y);

    fused_preprocess_kernel_bgr8_to_nchw32f<<<grid, block, 0, stream>>>(
        d_bgr, in_w, in_h, src_pitch_bytes, d_out, params);
}

#pragma once
#include <cuda_runtime.h>

#ifdef __cplusplus
extern "C" {
#endif

    void launch_fused_preprocess(
        const unsigned char* d_bgr, int in_w, int in_h, int in_pitch_bytes,
        float* d_out, int out_w, int out_h,
        const float mean[3], const float std_[3],
        cudaStream_t stream);

#ifdef __cplusplus
}
#endif

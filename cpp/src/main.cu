#include <cstdio>
#include <cuda_runtime.h>

int main() {
    int count = 0;
    cudaError_t err = cudaGetDeviceCount(&count);

    if (err != cudaSuccess) {
        printf("Erro ao obter número de devices CUDA: %s\n", cudaGetErrorString(err));
        return 1;
    }

    printf("Número de dispositivos CUDA: %d\n", count);

    for (int i = 0; i < count; i++) {
        cudaDeviceProp prop;
        cudaGetDeviceProperties(&prop, i);
        printf("#%d: %s | SM %d.%d | GlobalMem %.1f GB\n",
            i,
            prop.name,
            prop.major, prop.minor,
            prop.totalGlobalMem / (1024.0 * 1024.0 * 1024.0)
        );
    }

    return 0;
}

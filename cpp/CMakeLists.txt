cmake_minimum_required(VERSION 3.18)
project(tcc_gpu LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)

add_executable(device_info src/main.cu)

set_target_properties(device_info PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON
)

cmake_minimum_required(VERSION 3.18)

# Projeto com C++ e CUDA
project(tcc_gpu LANGUAGES CXX CUDA)

# Usar C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================
# Biblioteca C++ comum (Dijkstra + MST)
# ============================
# shortest_paths.cpp  -> dijkstra()
# mst.cpp             -> kruskal_mst()
add_library(tcc_cpp
    src/shortest_paths.cpp
    src/mst.cpp
)

# Headers estão em include/
target_include_directories(tcc_cpp
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# ============================
# Executável baseline_spmst
# ============================
# Usa a biblioteca tcc_cpp
add_executable(baseline_spmst
    src/baseline_spmst.cpp
)

target_link_libraries(baseline_spmst
    PRIVATE tcc_cpp
)

# ============================
# Executável CUDA já existente
# ============================
add_executable(device_info
    src/main.cu
)

set_target_properties(device_info PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON
)

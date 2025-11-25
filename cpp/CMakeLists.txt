cmake_minimum_required(VERSION 3.18)

# Projeto com C++ e CUDA
project(tcc_gpu LANGUAGES CXX CUDA)

# Usar C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================
# Biblioteca C++ com Dijkstra
# ============================
# src/shortest_paths.cpp implementa a função dijkstra()
add_library(tcc_cpp
    src/shortest_paths.cpp
)

# Dizer onde estão os headers (include/shortest_paths.hpp)
target_include_directories(tcc_cpp
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# ============================
# Executável de teste (Dijkstra)
# ============================
# src/test_shortest_paths.cpp tem o main() de teste
add_executable(test_shortest_paths
    src/test_shortest_paths.cpp
)

# Liga o executável à biblioteca tcc_cpp (onde está o dijkstra)
target_link_libraries(test_shortest_paths
    PRIVATE tcc_cpp
)

# ============================
# Executável CUDA
# ============================
add_executable(device_info
    src/main.cu
)

set_target_properties(device_info PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON
)

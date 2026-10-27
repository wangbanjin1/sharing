---
marp: true
theme: default
paginate: true
header: "🐿️ 松鼠分享会"
footer: "Ascend 310P 融合算子开发与入图全流程 | CANN ≥ 8.5.1 · ops-transformer v9.0.0"
style: |
  section {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    padding: 48px 64px;
    color: #18181b;
    background: #ffffff;
  }
  header {
    font-weight: 700;
    color: #92400e;
    background: #fef3c7;
    padding: 4px 12px;
    border-radius: 999px;
    top: 24px;
    right: 48px;
    left: auto;
  }
  h1 {
    font-size: 40px;
    color: #18181b;
  }
  h2 {
    font-size: 26px;
    border-bottom: 1px solid #e4e4e7;
    padding-bottom: 10px;
    margin-bottom: 20px;
  }
  code {
    background: #f4f4f5;
    color: #b45309;
    padding: 2px 6px;
    border-radius: 4px;
  }
  pre {
    background: #18181b !important;
    color: #f4f4f5 !important;
    border-radius: 8px;
    padding: 12px 16px;
  }
  table {
    font-size: 15px;
    width: 100%;
  }
  blockquote {
    border-left: 4px solid #d97706;
    background: #fffbeb;
    padding: 10px 16px;
    color: #78350f;
    font-size: 15px;
  }
---

<!-- _class: lead -->

# Ascend 310P 融合算子开发与入图全流程

**算子开发 → 算子编译出包 → ONNX 导入自定义算子 → 下沉至昇腾芯片构建可推理模型**

- **适用环境**：CANN ≥ 8.5.1 · `ops-transformer` v9.0.0 · Ascend 310P
- **开发范式**：Ascend C + Chrys (Bypass 模式) + 团队沉淀 Skills

---

## 01. 算子仓与环境准备

- **官方镜像优先（少折腾）**
  - 建议使用 **CANN 8.5.1** 及以上官方镜像（本地环境：`141.51.64.244`，容器：`ms_ops_cann8_5_1`）
- **算子仓库分支选择**
  ```bash
  git clone --depth 1 -b v9.0.0 https://gitcode.com/cann/ops-transformer.git
  ```
  - `v9.0.0` 分支在 CANN 8.5.1 和 9.0.0 下均稳定可用；`v8.5.1` 分支**不支持 Ascend 310P**，不建议使用
- **小网离线三方依赖准备**
  - 运行仓库内 `scripts/tools/third_lib_download.py`：`python third_lib_download.py`
  - 将下载的压缩包与依赖代码上传至服务器项目根目录下的 `third_party/` 目录

> 🖼️ **[图片预留位 #1 & #2]**（直接替换下方路径即可）：
> `![容器环境截图](./images/01_container_env.png)`
> `![third_party离线依赖目录](./images/02_third_party.png)`

---

## 02.1 算子编译、排障与出包安装

- **编译命令**（`--ops` 锚定存放算子的文件夹名，而非算子名）：
  ```bash
  bash build.sh --pkg --soc=ascend310p --ops=prompt_flash_attention \
    --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
  ```
- **典型报错与根因分析**
  - **现象**：`Invalid socVersion ascend950 of op ..., please check whether AddConfig are correctly configured in Opdef.`
  - **调用链**：`build.sh` → `cmake/scripts/prepare.sh` → `opbuild_gen_default`
  - **根因**：`opbuild` 遍历 `prompt_flash_attention_def.cpp` 中所有 `AddConfig`，310P 环境缺少 `ascend950` 完整配置
  - **修复**：在 `*_def.cpp` 中删除 `this->AICore().AddConfig("ascend950", aicoreConfig);`
- **安装与环境变量配置**
  ```bash
  ./build_out/cann-ops-transformer-custom_linux-aarch64.run
  export LD_LIBRARY_PATH=/usr/local/Ascend/cann-9.0.0/opp/vendors/custom_transformer/op_api/lib/:${LD_LIBRARY_PATH}
  ```

> 🖼️ **[图片预留位 #3 & #4]**（直接替换下方路径即可）：
> `![删除ascend950代码](./images/03_remove_ascend950.png)`
> `![build_out生成算子包](./images/04_build_out_pkg.png)`

---

## 02.2 算子生命周期与三级单测体系

**算子运行时完整生命周期**：
`设备初始化 (Init/SetDevice/Stream)` → `内存分配与数据拷贝` → `GetWorkspaceSize` → `分配 Workspace` → `启动 Kernel` → `SynchronizeStream` → `拷回 Host` → `清理资源`

| 维度 | `op_host` (`--ophost_test`) | `op_api` (`--opapi_test`) | `examples` (`--run_example`) |
| :--- | :--- | :--- | :--- |
| **测试范围** | 主机端 InferShape + Tiling | ACLNN API 包装层 | 完整端到端运行时 |
| **需要硬件** | 否（纯 CPU） | 是（需昇腾 NPU） | 是（需昇腾 NPU） |
| **测试框架** | gtest | gtest | 独立可执行文件 |
| **验证方式** | 形状 / tilingKey 对比 | 返回码检查 | 结果打印 / 人工审查 |

```bash
bash build.sh -u --ophost_test --ops=prompt_flash_attention --cann_3rd_lib_path=...
bash build.sh -u --opapi_test  --ops=prompt_flash_attention --cann_3rd_lib_path=...
bash build.sh --run_example prompt_flash_attention eager --soc=ascend310p -j8 --cann_3rd_lib_path=...
```

> 🖼️ **[图片预留位 #5]**（直接替换下方路径即可）：
> `![三级单测通过截图](./images/05_unit_tests_passed.png)`

---

## 03.1 & 03.2 算子入图（一）：ONNX Plugin 与导出 OM

- **测试网络拓扑**：`Query → Linear → ReLU → Linear → NPUPromptFlashAttention → +残差 → Output`
- **Step 1：编译并部署 `onnx_plugin`**
  ```bash
  bash build.sh --onnxplugin --soc=ascend310p --ops=prompt_flash_attention --cann_3rd_lib_path=...
  cp build/libop_transformer_onnx_plugin.so \
     /usr/local/Ascend/cann-9.0.0/opp/vendors/custom_transformer/built-in/framework/onnx/
  ```
- **Step 2：对齐 `OriginOpType` 创建 ONNX 节点并执行 ATC 转换**
  - Plugin 注册了 `ai.onnx::12::NPUPromptFlashAttention`，ONNX 节点 `op_type` 设为 `"NPUPromptFlashAttention"`，`domain=""`
  - ATC 转换命令：
    ```bash
    atc --model=prompt_flash_attention2.onnx --framework=5 --output=./test_om2 --soc_version=Ascend310P3
    ```

> 🖼️ **[图片预留位 #6 & #7]**（直接替换下方路径即可）：
> `![原始示例ONNX结构图](./images/06_onnx_graph.png)`
> `![ATC转换后OM模型图](./images/07_om_netron.png)`

---

## 03.3 算子入图（二）：导出 MindIR 模型与 GE Dump 图验证

- **OM vs MindIR：ONNX 节点定义差异**
  - MindSpore 在 CANN 基础上做了额外封装：ONNX 节点的 `op_type` 需统一写为 **`"Custom"`**，`domain="npu"`，真实算子名写在属性 `type="PromptFlashAttention"` 中
- **Converter Lite 转换命令**
  ```bash
  /home/mindspore-lite-2.8.0-linux-aarch64/tools/converter/converter/converter_lite \
    --fmk=ONNX --modelFile=/path/youronnx --outputFile=model --saveType=MINDIR --optimize=ascend_oriented
  ```
- **可视化验证技巧**
  - MindIR 无法直接用 Netron 观察下沉算子，设置 `export DUMP_GE_GRAPH=2` 后重新转换，用 Netron 打开最后阶段的 GE Dump 图

> 🖼️ **[图片预留位 #8 & #9]**（直接替换下方路径即可）：
> `![GE Dump图Netron可视化](./images/08_mindir_dump_netron.png)`
> `![MindIR推理测试结果](./images/09_mindir_infer_ok.png)`

---

## 04.1 需求案例：开发 MatMul+Add+Softmax+ReLU 融合算子

- **需求目标**
  - 开发 `float16` 类型的 `MatMul + Add + Softmax + ReLU` 四算子融合算子
- **AI 辅助实现过程**
  - 借助 **Chrys 的 bypass 模式**自动完成算子开发、编译检查、单测编写与迭代修改
  - 针对疑难报错，手动查阅 CANN 官方文档后为 Agent 提供排障方向，继续推进闭环
- **参考工作流 Wiki**
  - Ascend C 算子开发：`WIKI2026062711632135`
  - 服务器安装 Chrys：`WIKI2026070711750885`

> 🖼️ **[图片预留位 #10 & #11]**（直接替换下方路径即可）：
> `![融合算子结构图](./images/10_fused_op_arch.png)`
> `![Chrys开发过程截图](./images/11_chrys_bypass.png)`

---

## 04.2 最终验证效果与沉淀 Skills

- **单测与入图验证全部通过**
  - **`op_host` 单测通过**：算子形状推断（InferShape）与 Tiling 正常
  - **`op_api` 单测通过**：算子在 NPU 上调用结果正确
  - **模型转换测试通过**：融合算子可被正常识别并转换入图
- **团队可复用 Skills 沉淀**
  - 仓库地址：`https://codehub-y.huawei.com/nrm4/model/operator/files?ref=skills%2Fw00939968`

> 🖼️ **[图片预留位 #12 ~ #14]**（直接替换下方路径即可）：
> `![op_host单测通过](./images/12_ophost_pass.png)`
> `![op_api单测通过](./images/13_opapi_pass.png)`
> `![算子转换识别成功](./images/14_fused_op_convert.png)`

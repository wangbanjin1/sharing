---
marp: true
theme: default
paginate: true
header: "🐿️ 松鼠分享会"
footer: "Ascend 310P 融合算子开发与入图全流程 | CANN ≥ 8.5.1 · ops-transformer v9.0.0"
style: |
  section {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    padding: 44px 60px;
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
    font-size: 38px;
    color: #18181b;
  }
  h2 {
    font-size: 25px;
    border-bottom: 1px solid #e4e4e7;
    padding-bottom: 10px;
    margin-bottom: 16px;
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
    padding: 10px 14px;
  }
  table {
    font-size: 14px;
    width: 100%;
  }
  blockquote {
    border-left: 4px solid #d97706;
    background: #fffbeb;
    padding: 8px 14px;
    color: #78350f;
    font-size: 14px;
  }
---

<!-- _class: lead -->

# Ascend 310P 融合算子开发与入图全流程

**算子开发 → 算子编译出包 → ONNX 导入自定义算子 → 下沉到 Ascend 芯片构建可推理的模型**

- **环境基线**：CANN ≥ 8.5.1 · `ops-transformer` v9.0.0 · Ascend 310P
- **开发范式**：Ascend C + Chrys (Bypass 模式) + 总结 Skills

---

## 1. 准备算子仓和环境 & 2.1 离线依赖下载

- **镜像源与环境（少折腾）**
  - 官方镜像源：`https://www.hiascend.com/developer/ascendhub/detail/17da20d1c2b6493cb38765adeba85884`
  - 建议使用 CANN 8.5.1 以上环境；本地环境：`141.51.64.244`，容器：`ms_ops_cann8_5_1`
- **算子仓拉取**
  ```bash
  git clone --depth 1 -b v9.0.0 https://gitcode.com/cann/ops-transformer.git
  ```
  - `v9.0.0` 在 CANN 8.5.1 和 9.0.0 都能正常使用且更稳定；`v8.5.1` 不支持 Ascend 310P
- **2.1 第三方依赖离线下载（小网环境）**
  - 运行 `scripts/tools/third_lib_download.py`：`python third_lib_download.py`
  - 下载产物上传至项目根目录下 `third_party` 路径（如 `/dataset/personal/w00939968/Ascend/ops-transformer/third_party`）

> 🖼️ **原文图 #1 & #2**：
> - 图 #1：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/089d0945e74da8dfd9dd4271a220f819_1861x923.png@900-0-90-f.png)`
> - 图 #2：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/3ce50e506c9d8ab62211cdf6fe13c7e5_1027x498.png@900-0-90-f.png)`

---

## 2.1 算子编译、排障与出包安装

- **编译命令**（`--ops` 锚定存放算子的文件夹路径，而非算子名）：
  ```bash
  bash build.sh --pkg --soc=ascend310p --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
  ```
- **报错现象与根因分析**
  - **现象**：`Invalid socVersion ascend950 of op AddExample, please check whether AddConfig are correctly configured in Opdef.`
  - **调用链**：`build.sh` → `cmake/scripts/prepare.sh` → `opbuild_gen_default`
  - **根因**：`opbuild` 遍历 `prompt_flash_attention_def.cpp` 中所有已配置的 soc 版本（含 `ascend950`），但 310p 环境中 `ascend950` 配置不完整，删除红框中 `this->AICore().AddConfig("ascend950", aicoreConfig);` 即可
- **安装算子包与环境变量**
  ```bash
  ./build_out/cann-ops-transformer-custom_linux-aarch64.run
  export LD_LIBRARY_PATH=/usr/local/Ascend/cann-9.0.0/opp/vendors/custom_transformer/op_api/lib/:${LD_LIBRARY_PATH}
  ```

> 🖼️ **原文图 #3 & #4**：
> - 图 #3（删除红框代码）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/fd9fc9445fd6b1319513c16b00189b7c_1514x1060.png@900-0-90-f.png)`
> - 图 #4（`build_out` 生成算子包）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/e90fdfb40556b2cd1cd5ec7d73e66ffd_2530x603.png@900-0-90-f.png)`

---

## 2.2 算子单测（一）：完整生命周期与 `op_host` 测试

**完整生命周期**：
`设备初始化 (aclInit/SetDevice/CreateStream)` → `设备内存分配+Tensor创建+数据拷贝` → `获取 workspace 大小` → `分配 workspace 内存` → `启动 kernel` → `等待完成 (SynchronizeStream)` → `结果回拷主机+打印` → `清理资源`

| 维度 | `op_host` | `op_api` | `examples` |
| :--- | :--- | :--- | :--- |
| **测试范围** | 主机端 InferShape + Tiling | ACLNN API 包装层 | 完整端到端运行时 |
| **是否需要硬件** | 否（纯 CPU） | 是（需要昇腾 NPU） | 是（需要昇腾 NPU） |
| **测试框架 / 验证** | gtest / 形状与 tilingKey 对比 | gtest / 返回码检查 | 独立可执行文件 / 结果打印审查 |

- **`op_host` 测试命令**（`-u` 代表开启单元测试）：
  ```bash
  bash build.sh -u --ophost_test --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
  ```

> 🖼️ **原文图 #5**（`op_host` 形状推断测试通过）：
> `![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/0ec3d1bec9f162504f40ed430e571b18_1385x1103.png@900-0-90-f.png)`

---

## 2.2 算子单测（二）：`op_api` 测试与 `examples` 测试

- **`op_api` 测试命令**：
  ```bash
  bash build.sh -u --opapi_test --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
  ```
- **`examples` 测试命令**：
  ```bash
  bash build.sh --run_example prompt_flash_attention eager --soc=ascend310p -j8 --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
  ```

> 🖼️ **原文图 #6 & #7**：
> - 图 #6（`op_api` 测试通过）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/62c92be24a6e920ae12b4ad2ab71af45_1657x889.png@900-0-90-f.png)`
> - 图 #7（`examples` 测试通过）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/0ffc269a69851db58755404b4ca9958a_1661x774.png@900-0-90-f.png)`

---

## 3. 算子入图 & 3.1 `onnx_plugin` 编译导入

- **模型格式与示例网络结构**
  - 生产环境使用 `om` 模型（依托 CANN）和 `mindir` 模型（基于 MindSpore）
  - 示例网络结构：`Query → Linear → ReLU → Linear → NPUPromptFlashAttention → +残差 → Output`
- **3.1 `onnx_plugin` 编译导入**
  ```bash
  bash build.sh --onnxplugin --soc=ascend310p --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
  ```
  - 完成后在 `build` 路径下得到 `.so` 文件，拷贝至算子路径下让 `ge` 识别：
  ```bash
  cp build/libop_transformer_onnx_plugin.so /usr/local/Ascend/cann-9.0.0/opp/vendors/custom_transformer/built-in/framework/onnx/
  ```

> 🖼️ **原文图 #8 & #9**：
> - 图 #8（示例网络结构图）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/9b7c631e633d813a31a6298a99f93938_823x692.png@900-0-90-f.png)`
> - 图 #9（`libop_transformer_onnx_plugin.so` 产物）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/8ca9d8f0048cff07624dba722ec2d90b_1841x173.png@900-0-90-f.png)`

---

## 3.2 导出 OM 时引入自定义算子

- **将算子 `type` 与 `onnx_plugin` 对齐**
  - `NPUPromptFlashAttention` 是 ONNX 算子需使用的名称，前缀 `ai.onnx::xx` 由 `opset.version = 12` 控制
  ```python
  node_attention = make_node(
      "NPUPromptFlashAttention",
      inputs=["query_enhanced", "key_id", "value_id"],
      outputs=["attention_raw"], name="PromptFlashAttention", domain=""
  )
  # 挂载 type="PromptFlashAttention", input_names, output_names, num_heads=8 等属性
  ```
- **ATC 转换命令**
  ```bash
  atc --model=prompt_flash_attention2.onnx --framework=5 --output=./test_om2 --soc_version=Ascend310P3
  ```

> 🖼️ **原文图 #10**（转换后得到的 OM 模型图）：
> `![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/98b2aa9d1dbd15221680eaffb716eacc_964x680.png@900-0-90-f.png)`

---

## 3.3 导出 MindIR 时引入自定义算子

- **MindSpore 封装下的 ONNX 节点定义**
  - 节点的 `type` 统一写成 `Custom`，`domain="npu"`，而把 `attributes` 里的 `type` 写成被定义的算子 `PromptFlashAttention`
- **转换与 GE Dump 图可视化**
  ```bash
  /home/mindspore-lite-2.8.0-linux-aarch64/tools/converter/converter/converter_lite --fmk=ONNX --modelFile=/path/youronnx --outputFile=model --saveType=MINDIR --optimize=ascend_oriented
  ```
  - MindIR 无法用 Netron 直接可视化，使用 `export DUMP_GE_GRAPH=2` 再转化一次，选取最后一个阶段的 dump 图用 Netron 打开

> 🖼️ **原文图 #11 ~ #13**：
> - 图 #11（选取最后阶段 dump 图）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/c3e5e5b53fd5421d2f0effaf1892c092_2389x246.png@900-0-90-f.png)`
> - 图 #12（使用 Netron 打开）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/3b75d1f71e14e53bb2c4aa8c5fa75b2d_722x597.png@900-0-90-f.png)`
> - 图 #13（测试转换得到的 MindIR 功能正常）：`![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/b0e1dd02f74f2ecdfc16436926699dd2_2235x606.png@900-0-90-f.png)`

---

## 4.1 需求案例与实现过程：融合算子开发

- **工作流参考**
  - Ascend C 算子开发：`https://wiki.huawei.com/domains/143305/wiki/284021/WIKI2026062711632135`
  - 服务器安装 Chrys：`https://wiki.huawei.com/domains/143305/wiki/284021/WIKI2026070711750885`
- **需求案例**
  - 开发一个 `float16` 类型的 `matmul+add+softmax+relu` 的融合算子
- **实现过程**
  - 借助 chrys 的 bypass 模式完成算子开发、编译检查、单测编写和修改。中间过程较为曲折，有些报错需要手动去 CANN 官方查给它方向再继续运行

> 🖼️ **原文图 #14 & #15**：
> - 图 #14（融合算子结构）：`![image](https://wiki.huawei.com/vision-file-storage/api/file/download/upload-v2/WIKI2026071311839967/47004659/8408f27b740143d4b49d346a0088d134.png)`
> - 图 #15（Chrys bypass 实现过程）：`![image](https://wiki.huawei.com/vision-file-storage/api/file/download/upload-v2/WIKI2026071311839967/47004963/bd95355ca4d248c6a5ccaf1fbb8339f8.png)`

---

## 4.2 最后效果与总结 Skills

- **最后效果**
  - `op_host` 单测和 `op_api` 单测均通过，前者测试算子能否正常推断形状，后者测试算子调用的正确性
- **算子转换测试结果**
  - 算子可正常被识别转换
- **总结的 Skills**
  - `https://codehub-y.huawei.com/nrm4/model/operator/files?ref=skills%2Fw00939968`

> 🖼️ **原文图 #16 ~ #18**：
> - 图 #16（`op_host` 单测通过）：`![image](https://wiki.huawei.com/vision-file-storage/api/file/download/upload-v2/WIKI2026071311839967/47005133/71bd93fa53b448dd9da44ca3ee5373d7.png)`
> - 图 #17（`op_api` 单测通过）：`![image](https://wiki.huawei.com/vision-file-storage/api/file/download/upload-v2/WIKI2026071311839967/47005155/55946fcb874c45bb9b35892ca36c370a.png)`
> - 图 #18（算子转换测试结果）：`![image](https://wiki.huawei.com/vision-file-storage/api/file/download/upload-v2/WIKI2026071311839967/47005201/6ce4fe7c24e2493a9e0a5fa60ab5bb56.png)`

# Ascend 310P 融合算子开发与入图全流程

> 基于 CANN 最新开放的框架，支持在 Ascend 310P 上开发融合 Ascend C 算子，全流程包含：算子开发 → 算子编译出包 → ONNX 导入自定义算子 → 下沉到 Ascend 芯片构建可推理的模型

- **演示文稿（HTML 交互版）**：[index.html](./index.html)
- **演示文稿（Marp Markdown 版）**：[slides.md](./slides.md)

---

## 1. 准备算子仓和环境

建议直接使用 Ascend 提供的官方镜像源，少折腾。
镜像源参考：

> https://www.hiascend.com/developer/ascendhub/detail/17da20d1c2b6493cb38765adeba85884

建议使用 CANN 8.5.1 以上的环境。本地环境使用：

> `141.51.64.244`  容器使用 `ms_ops_cann8_5_1`

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/089d0945e74da8dfd9dd4271a220f819_1861x923.png@900-0-90-f.png)

算子仓拉取：

```bash
git clone --depth 1 -b v9.0.0 https://gitcode.com/cann/ops-transformer.git
```

`v9.0.0` 的代码分支在 CANN 8.5.1 和 CANN 9.0.0 都能正常使用，`v8.5.1` 分支代码不支持 Ascend 310P，不建议使用。`v9.0.0` 更稳定，因此文档后续在该分支完成。

---

## 2. 算子编译、出包、单测

### 2.1 算子编译

算子仓库依赖一些第三方依赖，服务器是小网环境，因此需要离线下载好放进去。
通过 [third_lib_download.py](https://gitcode.com/cann/ops-transformer/blob/master/scripts/tools/third_lib_download.py) 脚本一键下载，该脚本在本项目 `scripts/tools/` 目录，下载该脚本并执行如下命令：

```bash
python third_lib_download.py
```

下载后的依赖存放在下载脚本路径，下载产物是一些压缩包和依赖代码，上传到服务器的项目根目录下的 `third_party` 路径，例如 `/dataset/personal/w00939968/Ascend/ops-transformer/third_party`：

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/3ce50e506c9d8ab62211cdf6fe13c7e5_1027x498.png@900-0-90-f.png)

编译过程依赖项目根目录下的 `build.sh`，以 `prompt_flash_attention` 算子为例，编译命令如下：

```bash
bash build.sh --pkg --soc=ascend310p --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
```

`--ops` 命令锚定的是存放算子的文件夹路径，并不是算子的命名。
这里会遇到算子的不支持问题，现象：

```text
Invalid socVersion ascend950 of op AddExample, please check whether AddConfig are correctly configured in Opdef.
```

根因分析，调用链如下：

```text
build.sh --pkg --soc=ascend310p --ops=add_example
  → cmake/scripts/prepare.sh
  → opbuild_gen_default (从 autogen 目录生成代码)
```

`opbuild` 工具在 `prompt_flash_attention_def.cpp` 中找到了 3 个 `AddConfig`：

```cpp
this->AICore().AddConfig("ascend910b", aicoreConfig);    // 存在
this->AICore().AddConfig("ascend910_93", aicoreConfig);  // 存在
this->AICore().AddConfig("ascend950", aicoreConfig);     // 存在，但ascend310p环境不支持
```

当 `--soc=ascend310p` 传入时，`opbuild` 遍历所有已配置的 soc 版本，**包括 ascend950**。但 Ascend 310P 环境中 `ascend950` 的配置不完整，`opbuild` 尝试为 `ascend950` 生成代码时失败。

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/fd9fc9445fd6b1319513c16b00189b7c_1514x1060.png@900-0-90-f.png)

删除红框中的代码即可。
继续编译运行，成功后会在项目根目录的 `build_out` 路径下生成算子包：

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/e90fdfb40556b2cd1cd5ec7d73e66ffd_2530x603.png@900-0-90-f.png)

执行 `./build_out/cann-ops-transformer-custom_linux-aarch64.run` 安装算子包，同时添加算子的环境变量：

```bash
export LD_LIBRARY_PATH=/usr/local/Ascend/cann-9.0.0/opp/vendors/custom_transformer/op_api/lib/:${LD_LIBRARY_PATH}
```

到此，自定义算子出包和安装已经完成。

### 2.2 算子单测

一个 Ascend 算子在昇腾硬件上正确使用的完整生命周期：

```text
设备初始化 (aclInit + aclrtSetDevice + aclrtCreateStream)
→ 设备内存分配 + Tensor 创建 + 数据拷贝 (aclrtMalloc + aclCreateTensor + aclrtMemcpy)
→ 获取 workspace 大小 (aclnnPromptFlashAttentionV3GetWorkspaceSize)
→ 分配 workspace 内存
→ 启动 kernel (aclnnPromptFlashAttentionV3)
→ 等待完成 (aclrtSynchronizeStream)
→ 结果回拷到主机 + 打印 (aclrtMemcpy device→host)
→ 清理资源
```

总共包含三个测试模式，`op_host` 测试、`op_api` 测试、`examples` 测试，其具体对比差异如下：

| 维度 | op_host | op_api | examples |
| :--- | :--- | :--- | :--- |
| 测试范围 | 主机端 InferShape + Tiling | ACLNN API 包装层 | 完整端到端运行时 |
| 是否需要硬件 | 否（纯 CPU） | 是（需要昇腾 NPU） | 是（需要昇腾 NPU） |
| 测试框架 | gtest | gtest | 独立可执行文件 |
| 验证方式 | 形状/tilingKey 对比 | 返回码检查 | 结果打印/人工审查 |

`op_host` 测试使用命令如下（`-u` 代表开启单元测试）：

```bash
bash build.sh -u --ophost_test --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
```

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/0ec3d1bec9f162504f40ed430e571b18_1385x1103.png@900-0-90-f.png)

`op_api` 测试使用命令如下：

```bash
bash build.sh -u --opapi_test --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
```

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/62c92be24a6e920ae12b4ad2ab71af45_1657x889.png@900-0-90-f.png)

`examples` 测试使用命令如下：

```bash
bash build.sh --run_example prompt_flash_attention eager --soc=ascend310p -j8 --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
```

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/0ffc269a69851db58755404b4ca9958a_1661x774.png@900-0-90-f.png)

---

## 3. 算子入图

目前生产环境使用两种模型格式：`om` 模型和 `mindir` 模型，前者依托 CANN 的能力构建，后者基于 MindSpore 的能力构建。
示例网络结构：

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/9b7c631e633d813a31a6298a99f93938_823x692.png@900-0-90-f.png)

> Query → Linear → ReLU → Linear → NPUPromptFlashAttention → +残差 → Output

### 3.1 onnx_plugin 编译导入

```bash
bash build.sh --onnxplugin --soc=ascend310p --ops=prompt_flash_attention --cann_3rd_lib_path=/dataset/personal/w00939968/Ascend/ops-transformer/third_party
```

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/8ca9d8f0048cff07624dba722ec2d90b_1841x173.png@900-0-90-f.png)

拷贝 `.so` 到对应的算子路径下让 GE 识别：

```bash
cp build/libop_transformer_onnx_plugin.so /usr/local/Ascend/cann-9.0.0/opp/vendors/custom_transformer/built-in/framework/onnx/
```

### 3.2 导出 OM 时引入自定义算子

```cpp
REGISTER_CUSTOM_OP("PartitionedCall")
  .FrameworkType(ONNX)
  .OriginOpType({ge::AscendString("npu::1::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::11::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::12::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::13::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::14::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::15::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::16::NPUPromptFlashAttention"),
                 ge::AscendString("ai.onnx::19::NPUPromptFlashAttention")})
  .ParseParamsFn(ParseParamsPromptFlashAttention)
  .ParseOpToGraphFn(ParseOpToGraphNpuPromptFlashAttention)
  .ImplyType(ImplyType::TVM);
```

ONNX 创建算子代码片段参考：

```python
node_attention = make_node(
    "NPUPromptFlashAttention",
    inputs=["query_enhanced", "key_id", "value_id"],
    outputs=["attention_raw"],
    name="PromptFlashAttention",
    domain="",
)
attrs = [
    make_attribute("type", "PromptFlashAttention"),
    make_attribute("input_names", ["query", "key", "value"]),
    make_attribute("output_names", ["attention_out"]),
    make_attribute("num_heads", 8),
    make_attribute("scale_value", 1.0),
    make_attribute("pre_tokens", 214748647),
    make_attribute("next_tokens", 0),
    make_attribute("input_layout", "BSH"),
    make_attribute("num_key_value_heads", 8),
    make_attribute("sparse_mode", 0),
    make_attribute("inner_precise", 0),
]
node_attention.attribute.extend(attrs)
```

ATC 转换命令：

```bash
atc --model=prompt_flash_attention2.onnx --framework=5 --output=./test_om2 --soc_version=Ascend310P3
```

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/98b2aa9d1dbd15221680eaffb716eacc_964x680.png@900-0-90-f.png)

### 3.3 导出 MindIR 时引入自定义算子

MindSpore 框架在 CANN 的基础上做了额外的封装，定义 ONNX 算子时需要将节点的 `type` 统一写成 `Custom`，把 `attributes` 里的 `type` 写成被定义的算子：

```python
node_attention = make_node(
    "Custom",
    inputs=["query_enhanced", "key_id", "value_id"],
    outputs=["attention_raw"],
    name="PromptFlashAttention",
    domain="npu",
)
attrs = [
    make_attribute("type", "PromptFlashAttention"),
    make_attribute("input_names", ["query", "key", "value"]),
    make_attribute("output_names", ["attention_out"]),
    make_attribute("num_heads", 8),
    make_attribute("scale_value", 1.0),
    make_attribute("pre_tokens", 214748647),
    make_attribute("next_tokens", 0),
    make_attribute("input_layout", "BSH"),
    make_attribute("num_key_value_heads", 8),
    make_attribute("sparse_mode", 0),
    make_attribute("inner_precise", 0),
]
```

转换命令：

```bash
/home/mindspore-lite-2.8.0-linux-aarch64/tools/converter/converter/converter_lite --fmk=ONNX --modelFile=/path/youronnx --outputFile=model --saveType=MINDIR --optimize=ascend_oriented
```

使用 `export DUMP_GE_GRAPH=2` 导出 GE 图查看：

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/c3e5e5b53fd5421d2f0effaf1892c092_2389x246.png@900-0-90-f.png)

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/3b75d1f71e14e53bb2c4aa8c5fa75b2d_722x597.png@900-0-90-f.png)

![](http://image.huawei.com/tiny-lts/v1/images/hi3ms/b0e1dd02f74f2ecdfc16436926699dd2_2235x606.png@900-0-90-f.png)

---

## 4. 需求案例：开发 MatMul+Add+Softmax+ReLU 融合算子

- 工作流参考：
  - Ascend C 算子开发：`https://wiki.huawei.com/domains/143305/wiki/284021/WIKI2026062711632135`
  - 服务器安装 Chrys：`https://wiki.huawei.com/domains/143305/wiki/284021/WIKI2026070711750885`
- 总结的 Skills：`https://codehub-y.huawei.com/nrm4/model/operator/files?ref=skills%2Fw00939968`

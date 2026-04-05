# gepro: gerrit CI增强助手

## 系统需求

在gerrit和jenkins 持续集成中，已经开源的使用jenkins gerrit plugin可以很好的处理单个change的编译和打分，但是对于andriod repo中，多个用topic绑定的在多个仓库中改动的改动支持不好，尤其是topic绑定的多个patch，触发多个pipeline的情况，会出现重复启动，重复打分，缺失打分的情况，非常浪费ci资源。我们需要基于gerrit+ jenkins + jenkins gerrit plugin这样的工具链架构做一些增强。

假设有一个topic名字是t1_topic, 在gerrit中有两个改动gerrit_c1, gerrit_c2, 其中gerrit_c1需要启动两个jenkins流水线：p1_pipeline, p2_pipeline, gerrit_c2需要启动两个jenkins流水线：p2_pipeline, p3_pipeline, 那么我们只需要启动 p1_pipeline p2_pipeline p3_pipeline各一次，并且c1开始的时候，所有改动先gerrit 打分 0， 编译后打分-1或者+1. 为了实现这个目标，我们要做到下面几个需求：

1： ci启动入口： 所有gerrit仓库的改动会先通过启动一个hub_ci_job， 这个hub-ci-job用jenkins gerrit plugin启动，我们不用实现。
2： 功能点一： hub_ci_job中记录了gerrit trigger输入的参数，需要根据改动所在的仓库和仓库中文件的路径的正则表表达式，来决定去启动具体的pipeline，并且把gerrit trigger的所有参数传给具体的pipline. 这个映射关系存在一个json文件中，比如：
trigger_configs: {
   "p1_pipeline": [
        {  "path": "gerrit_repo1:path1/.*",  "mandantory": "true"},
        {  "path": "gerrit_repo2:.*",  "mandantory": "false"},  
    ],
   "p2_pipeline": [
        {  "path": "gerrit_repo2:path2/.*",  "mandantory": "true"},
        {  "path": "gerrit_repo2:.*",  "mandantory": "false"},    
    ],
}
表示gerrit_repo1的path1中的所有文件（.*为正则匹配），
### 


#细分提示词

hub_ci_job中记录了gerrit trigger输入的参数，需要根据改动所在的仓库和仓库中文件的路径的正则表表达式，来决定去启动具体的pipeline，并且把gerrit trigger的所有参数传给具体的pipline. 这个映射关系存在一个json文件中，比如：

### DCI CLI 核心功能模块开发文档

#### 项目概述

DCI（Distributed CI）是一个基于 Python 构建的分布式持续集成编排工具。它旨在作为 Gerrit 代码审查系统与 Jenkins 自动化服务器之间的“智能桥梁”。通过解析本地配置文件，DCI 能够根据代码变更的上下文（如修改的文件路径、变更 ID）自动决策并触发相应的 Jenkins 流水线，从而实现精细化的 CI/CD 流程控制。

#### 核心功能模块架构

**命令行交互模块**
该模块是用户与系统交互的入口，基于 Click 框架构建，负责指令解析与流程引导。

- **启动优化**：摒弃繁琐的 `python -m` 调用方式，支持通过本地脚本（如 `./dci`）直接启动，模拟原生应用的执行体验。
- **Info 诊断命令**：新增 `info` 子命令，专门用于展示系统状态。执行该命令时，系统应调用 Banner 打印函数，在终端渲染出具有视觉冲击力的 ASCII 图形（支持随机暖色调），并显示当前的版本号与环境元数据。
- **装饰器规范**：严格遵循 Click 开发规范，`info` 等叶子命令仅使用 `@cli.command()` 装饰，严禁混用 `@click.group()`，确保上下文传递的稳定性。

**智能触发引擎**
这是 DCI 的核心业务逻辑模块，负责处理代码变更事件并决策是否触发构建。

- **配置驱动**：引擎启动时，首先加载用户指定的 JSON 配置文件（通过 `--config` 参数指定）。该文件定义了项目结构与流水线之间的映射关系。
- **规则匹配逻辑**：
    - **文件路径匹配**：系统根据 Gerrit 变更 ID 获取受影响的文件列表，并将其与配置文件中的 `match_paths`（正则表达式）进行比对。
    - **全局忽略策略**：支持在配置中定义 `global_ignore` 规则（如文档目录、README 文件），凡命中忽略规则的文件变更将不触发任何流水线，避免无效构建。
    - **流水线决策**：只有当变更文件命中特定规则且未被忽略时，对应的 Jenkins 流水线才会被标记为“待触发”。
- **干跑模式**：提供 `--dry-run` 选项，允许用户在不实际调用 Jenkins 接口的情况下，预览哪些流水线会被触发，便于验证配置文件的正确性。

**Gerrit 客户端模块**
该模块封装了与 Gerrit 服务器的交互逻辑，主要负责获取代码审查的元数据。

- **变更查询**：根据传入的 `Change-ID`，调用 Gerrit REST API 获取变更的详细信息，包括提交人、主题以及最重要的“修改文件列表”。
- **打分服务**：提供 `score` 子命令，允许用户通过 CLI 直接对 Gerrit 上的变更进行打分（如 `Code-Review+1` 或 `Verified-1`）。这通常用于在 CI 流程结束后，自动回写构建结果到代码审查系统。

**Jenkins 客户端模块**
该模块负责与 Jenkins 自动化服务器进行通信，执行实际的构建任务。

- **任务触发**：封装 Jenkins 的构建 API，接收来自触发引擎的指令。它支持传递构建参数（如 `GERRIT_CHANGE_ID`、`GERRIT_EVENT_TYPE`），确保 Jenkins 流水线能够感知到当前的构建是由哪个代码变更引起的。
- **状态反馈**：虽然当前版本主要关注触发，但该模块设计上也预留了查询构建状态的能力，以便未来实现同步等待构建结果的功能。

**通用工具模块**
提供系统层面的基础支持，确保用户体验的一致性与美观性。

- **动态 Banner 渲染**：实现了从外部文件（`resource/banner.txt`）加载 ASCII 图形，并结合随机暖色调（如夕阳橙、樱花粉）进行渲染的功能。这不仅增加了工具的辨识度，也让枯燥的命令行操作多了一份趣味。
- **日志与色彩系统**：定义了统一的日志输出接口 `info_color`，支持 `INFO`、`ERROR`、`WARNING` 等不同级别的色彩区分，确保关键信息在终端中清晰可见。
- **资源路径管理**：提供了 `get_resource_path` 函数，自动处理开发环境与打包环境下的文件路径差异，确保配置文件与资源文件的稳定加载。

#### 数据流转与配置规范

DCI 的运行依赖于结构化的 JSON 配置文件。该文件定义了 `pipelines` 字典，键为 Jenkins 任务名称，值包含具体的触发规则。

- **输入流**：用户输入 `dci trigger -c conf.json -cid I12345`。
- **处理流**：
    - 系统加载 `conf.json`。
    - 调用 Gerrit 模块获取 `I12345` 对应的文件列表（例如 `src/main.java`）。
    - 遍历 `conf.json` 中的规则，发现 `src/.*\.java` 匹配 `backend-pipeline`。
    - 检查忽略规则，确认未被忽略。
- **输出流**：调用 Jenkins 模块触发 `backend-pipeline`，并在终端输出 `[NOTES] 触发流水线: backend-pipeline`。

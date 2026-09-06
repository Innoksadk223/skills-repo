# 清理清单

## 编译运行时残留

```
__pycache__/          Python 字节码缓存
*.pyc                 Python 编译文件
*.pyo                 Python 优化编译文件
*.class               Java 编译文件
*.o *.obj             C/C++ 编译产物
build/ dist/ *.egg-info/   Python 构建产物
target/               Rust/Java 构建目录
.gradle/              Gradle 缓存
```

## 包管理器残留

```
node_modules/         仅本次安装且最终未使用的
package-lock.json     本次改动且无效的变化
venv/ .venv/          仅本次创建且任务不再需要的
Pipfile.lock          本次安装但未使用的变化
```

## 文件系统垃圾

```
.DS_Store             macOS 目录元数据
Thumbs.db             Windows 缩略图
*~                    Emacs/Vim 备份
*.bak                 备份文件
*.orig                Merge 原始文件
*.swp *.swo           Vim 交换文件
```

## 临时调试代码

### Python
```python
print(...)             未注释的调试打印
pdb.set_trace()        断点
import pdb; pdb.set_trace()
logging.debug(...)     未配置的调试日志
```

### JavaScript/TypeScript
```javascript
console.log(...)       调试打印
debugger;              断点语句
console.debug(...)
```

### 通用
- 硬编码的 API key、token、密码
- 测试账号凭据
- 误提交的 `.env`、`credentials.json`
- 假数据、placeholder 值

## 临时产出物

- 本次创建且确认无用的测试截图/导出
- 本次失败构建产生且确认无用的中间产物
- 本次创建、确认无内容且不会影响用户或其他 agent 工作的空目录
- 一次性脚本：数据处理、格式转换、临时自动化（本次创建且任务完成后不再需要）
- 本次创建、未被采用且确认无用的方案文件

## 过程测试文件

本次为验证而新增的测试代码或夹具可能具有回归价值，不默认视为垃圾：

1. 区分测试代码/夹具与测试截图、缓存、导出等明确临时产物。
2. 列出拟删除文件的具体路径，以及任务结束后不再需要的理由。
3. 仅在用户明确确认后删除；未确认时保留并写入“保留待确认”。

## 不确定归属的

以下情况**保留并报告**：

- 文件被用户改过，原始内容不确定
- 无法确认是否属于本次任务
- 可能是其他工作流需要的
- 删除可能影响其他 agent 或用户手动工作

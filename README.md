# e-mars
MARS agent for U-CASA

## Usage
これまでのMARS使用システムのimportを下記のように変更するだけで使用可能  
```python
from cas_agent import CasWorkerAgent
```
その他の使用例はTest内参照のこと  

## 変更点
EdgeBaseAgent拡張のCasBaseAgent実装  
それをもとにCasWorkerAgent, CasManagementAgent, CasConsoleAgent実装  
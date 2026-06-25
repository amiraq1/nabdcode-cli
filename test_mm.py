import sys
import os
try:
    from nabdcode.core.model_manager import ModelManager
    print("SUCCESS")
    print(dir(ModelManager))
except Exception as e:
    print("FAILED:", type(e), e)

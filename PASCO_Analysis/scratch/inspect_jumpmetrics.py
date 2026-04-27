import jumpmetrics
from jumpmetrics.core.processors import ForceTimeCurveCMJTakeoffProcessor
import pandas as pd
import numpy as np

# Load dummy data to inspect events
force = np.random.normal(700, 10, 5000) # Dummy force
# Try to instantiate and check attributes
try:
    processor = ForceTimeCurveCMJTakeoffProcessor(force_series=pd.Series(force), sampling_frequency=1000)
    print("Events available in processor:")
    # We might need to run get_jump_events() first
    # But let's see the class structure via dir()
    print(dir(processor))
except Exception as e:
    print(f"Error: {e}")

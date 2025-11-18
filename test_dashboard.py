"""
MINIMAL TEST VERSION - Use this to verify Streamlit Cloud works
If this works, the issue is with your main dashboard.py
If this fails too, the issue is with Streamlit Cloud setup
"""

import streamlit as st

st.title("🧪 Streamlit Cloud Test")

st.write("## Step 1: Basic Streamlit ✅")
st.write("If you see this, Streamlit is working!")

# Test pandas
try:
    import pandas as pd
    st.write("## Step 2: Pandas ✅")
    st.write("Pandas version:", pd.__version__)
except Exception as e:
    st.error(f"❌ Pandas failed: {e}")

# Test plotly - THIS IS THE CRITICAL TEST
try:
    import plotly.express as px
    import plotly.graph_objects as go
    st.write("## Step 3: Plotly ✅")
    st.write("Plotly version:", px.__version__)
    
    # Create a simple chart to prove it works
    import pandas as pd
    df = pd.DataFrame({
        'x': [1, 2, 3, 4, 5],
        'y': [2, 4, 6, 8, 10]
    })
    fig = px.line(df, x='x', y='y', title='Test Chart')
    st.plotly_chart(fig)
    st.success("🎉 PLOTLY WORKS! Your issue is elsewhere.")
    
except Exception as e:
    st.error(f"❌ Plotly failed: {e}")
    st.write("This means requirements.txt is not being read correctly.")
    
    # Debug info
    import sys
    st.write("### Debug Info:")
    st.write("Python version:", sys.version)
    st.write("Python path:", sys.executable)
    
    # Try to show installed packages
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                              capture_output=True, text=True)
        st.write("### Installed Packages:")
        st.code(result.stdout)
    except:
        st.write("Could not list packages")

# Test other dependencies
try:
    import openpyxl
    st.write("## Step 4: Openpyxl ✅")
except Exception as e:
    st.error(f"❌ Openpyxl failed: {e}")

try:
    import requests
    st.write("## Step 5: Requests ✅")
except Exception as e:
    st.error(f"❌ Requests failed: {e}")

st.write("---")
st.write("## 📋 Next Steps:")
st.write("""
If Plotly shows ✅ above:
- Your requirements.txt IS working
- The issue is in your main dashboard.py
- Check for import errors elsewhere in the file

If Plotly shows ❌ above:
- requirements.txt is NOT being read
- Check file location (must be in repo root)
- Try deleting and recreating the app
- See EMERGENCY_FIX_PLOTLY.md for solutions
""")

import plotly.graph_objects as go
import numpy as np
import statsmodels.api as sm
from sklearn.preprocessing import PolynomialFeatures
import json

def create_interactive_3d_report(df, x_col, y_col, z_col, x_label, y_label, z_label, title, output_path):
    """
    建立具備二階多項式曲面與「正式分界平面」的互動式 3D 專業運動表現報告。
    每位球員為獨立 trace，篩選面板可即時控制每個球員點的顯示/隱藏。
    """
    # 1. 建立模型 (二階多項式)
    X_vals = df[[x_col, y_col]]
    poly = PolynomialFeatures(degree=2, include_bias=True)
    X_poly = poly.fit_transform(X_vals)
    y_vals = df[z_col]
    model_poly = sm.OLS(y_vals, X_poly).fit()

    df['Predicted'] = model_poly.predict(X_poly)
    df['Residual'] = df[z_col] - df['Predicted']

    # 2. 獲取資料範圍與平均值
    x_min, x_max = df[x_col].min(), df[x_col].max()
    y_min, y_max = df[y_col].min(), df[y_col].max()
    z_min, z_max = df[z_col].min(), df[z_col].max()
    x_avg, y_avg, z_avg = df[x_col].mean(), df[y_col].mean(), df[z_col].mean()
    res_min, res_max = df['Residual'].min(), df['Residual'].max()

    # 3. 準備繪圖
    fig = go.Figure()

    # --- A. 理想轉化曲面 (主視覺) ---   [trace 0]
    x_range = np.linspace(x_min * 0.9, x_max * 1.1, 50)
    y_range = np.linspace(y_min * 0.9, y_max * 1.1, 50)
    XX, YY = np.meshgrid(x_range, y_range)
    mesh_points = np.c_[XX.ravel(), YY.ravel()]
    poly_mesh = poly.transform(mesh_points)
    ZZ = model_poly.predict(poly_mesh).reshape(XX.shape)

    fig.add_trace(go.Surface(
        x=x_range, y=y_range, z=ZZ,
        opacity=0.4, colorscale='Viridis', showscale=False,
        name='預期表現曲面', hoverinfo='skip'
    ))  # trace 0

    # --- B. 專業分界平面 ---   [trace 1, 2, 3]
    fig.add_trace(go.Surface(
        x=[x_avg, x_avg], y=[y_min*0.9, y_max*1.1],
        z=[[z_min*0.9, z_max*1.1], [z_min*0.9, z_max*1.1]],
        opacity=0.15, showscale=False, colorscale=[[0,'gray'],[1,'gray']],
        name='RFD 基準面', hoverinfo='skip'
    ))  # trace 1
    fig.add_trace(go.Surface(
        x=[x_min*0.9, x_max*1.1], y=[y_avg, y_avg],
        z=[[z_min*0.9, z_min*0.9], [z_max*1.1, z_max*1.1]],
        opacity=0.15, showscale=False, colorscale=[[0,'gray'],[1,'gray']],
        name='SJ 基準面', hoverinfo='skip'
    ))  # trace 2
    fig.add_trace(go.Surface(
        x=[x_min*0.9, x_max*1.1], y=[y_min*0.9, y_max*1.1],
        z=[[z_avg, z_avg], [z_avg, z_avg]],
        opacity=0.1, showscale=False, colorscale=[[0,'blue'],[1,'blue']],
        name='速度基準面', hoverinfo='skip'
    ))  # trace 3

    # --- C. 每位球員獨立一條 Scatter3d trace ---   [trace 4 ~ 4+N-1]
    player_ids = sorted(df['Player_ID'].unique().tolist())
    PLAYER_TRACE_START = 4  # 前面 Surface × 4 佔了 index 0-3

    for i, pid in enumerate(player_ids):
        pdata = df[df['Player_ID'] == pid]
        show_cb = (i == 0)  # 只有第一條 trace 顯示 colorbar
        fig.add_trace(go.Scatter3d(
            x=pdata[x_col], y=pdata[y_col], z=pdata[z_col],
            mode='markers+text',
            text=[pid] * len(pdata),
            textposition='top center',
            marker=dict(
                size=6,
                color=pdata['Residual'].tolist(),
                colorscale='RdYlGn',
                cmin=res_min, cmax=res_max,
                showscale=show_cb,
                colorbar=dict(title='轉換效率 (殘差)', thickness=15, x=1.1) if show_cb else None
            ),
            name=f'球員 {pid}',
            showlegend=False,
            hovertemplate=(
                f'<b>球員: {pid}</b><br>'
                + x_label + ': %{x:.2f}<br>'
                + y_label + ': %{y:.2f}<br>'
                + z_label + ': %{z:.2f}<extra></extra>'
            )
        ))  # trace 4+i

    # --- D. 象限定義標籤 ---   [trace 4+N ~ 4+N+7]
    x_off = (x_max - x_min) * 0.15
    y_off = (y_max - y_min) * 0.15
    z_off = (z_max - z_min) * 0.15

    quadrant_defs = [
        (x_max+x_off, y_max+y_off, z_max+z_off, '<b>[高發力/高力量/高速度]</b><br>全項素質優異且成功轉換'),
        (x_max+x_off, y_min-y_off, z_max+z_off, '<b>[高發力/低力量/高速度]</b><br>肌肉底子普普但發力與協調極佳'),
        (x_min-x_off, y_max+y_off, z_max+z_off, '<b>[低發力/高力量/高速度]</b><br>啟動雖慢但靠絕對肌力硬推速度'),
        (x_min-x_off, y_min-y_off, z_max+z_off, '<b>[低發力/低力量/高速度]</b><br>體能數值低但揮擊技術極效'),
        (x_max+x_off, y_max+y_off, z_min-z_off, '<b>[高發力/高力量/低速度]</b><br>身體素質極佳但傳導斷裂'),
        (x_min-x_off, y_max+y_off, z_min-z_off, '<b>[低發力/高力量/低速度]</b><br>壯漢但發力慢且無法轉換成速度'),
        (x_max+x_off, y_min-y_off, z_min-z_off, '<b>[高發力/低力量/低速度]</b><br>發力雖快但肌肉基礎力量不足'),
        (x_min-x_off, y_min-y_off, z_min-z_off, '<b>[低發力/低力量/低速度]</b><br>發力、肌力與技術皆需提升'),
    ]
    for qx, qy, qz, qtext in quadrant_defs:
        fig.add_trace(go.Scatter3d(
            x=[qx], y=[qy], z=[qz],
            mode='text', text=[qtext],
            textfont=dict(size=11, color='black'),
            name='原型定義', showlegend=False
        ))

    # --- E. 佈局優化 ---
    fig.update_layout(
        title=dict(text=title, font=dict(size=20)),
        scene=dict(
            xaxis=dict(title=x_label, backgroundcolor='rgb(240,240,240)', gridcolor='white',
                       range=[x_min - x_off*1.5, x_max + x_off*1.5]),
            yaxis=dict(title=y_label, backgroundcolor='rgb(240,240,240)', gridcolor='white',
                       range=[y_min - y_off*1.5, y_max + y_off*1.5]),
            zaxis=dict(title=z_label, backgroundcolor='rgb(240,240,240)', gridcolor='white',
                       range=[z_min - z_off*1.5, z_max + z_off*1.5]),
            camera=dict(eye=dict(x=2.2, y=2.2, z=1.5))
        ),
        margin=dict(l=0, r=0, b=0, t=60),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    fig.write_html(output_path)

    # ----------------------------------------------------------------
    # 注入球員篩選面板
    # 每位球員對應 trace index = PLAYER_TRACE_START + player_ids.index(pid)
    # ----------------------------------------------------------------
    pid_to_trace = {pid: PLAYER_TRACE_START + i for i, pid in enumerate(player_ids)}
    pid_to_trace_json = json.dumps(pid_to_trace)

    checkboxes_html = ''.join(
        f'<label><input type="checkbox" class="pf-cb" value="{pid}" checked> {pid}</label>'
        for pid in player_ids
    )

    filter_block = (
        """<style>
#player-filter-panel {
  position: fixed; top: 12px; right: 12px; z-index: 9999;
  background: rgba(255,255,255,0.96); border: 1px solid #ccc;
  border-radius: 10px; padding: 12px 16px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.15);
  font-family: 'Segoe UI', sans-serif; font-size: 13px;
  max-height: 90vh; overflow-y: auto; min-width: 160px;
}
#player-filter-panel h4 { margin: 0 0 8px 0; font-size: 14px; color: #333; }
.pf-btn-row { display: flex; gap: 6px; margin-bottom: 8px; }
.pf-btn {
  flex: 1; padding: 4px 0; font-size: 12px;
  border: 1px solid #aaa; border-radius: 5px; cursor: pointer; background: #f5f5f5;
}
.pf-btn:hover { background: #e0e0e0; }
.pf-checkbox-list { display: flex; flex-direction: column; gap: 4px; }
.pf-checkbox-list label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.pf-checkbox-list input[type=checkbox] { width: 14px; height: 14px; cursor: pointer; }
</style>
<div id="player-filter-panel">
  <h4>&#128269; 球員篩選</h4>
  <div class="pf-btn-row">
    <button class="pf-btn" onclick="pfSelectAll()">全選</button>
    <button class="pf-btn" onclick="pfClearAll()">清除</button>
  </div>
  <div class="pf-checkbox-list" id="pf-list">"""
        + checkboxes_html
        + """  </div>
</div>
<script>
(function () {
  // 球員 ID → Plotly trace index 對照表（由 Python 直接嵌入）
  var PID_TO_TRACE = """ + pid_to_trace_json + """;
  var gd = null;

  // 輪詢等待 Plotly 初始化完成（_fullData 是 Plotly 內部就緒的旗標）
  function waitForPlotly() {
    var el = document.querySelector('.plotly-graph-div');
    if (el && el._fullData && el._fullData.length > 0) {
      gd = el;
    } else {
      setTimeout(waitForPlotly, 50);
    }
  }

  // 每次 checkbox 變動後，對對應 trace 設定 visible
  function applyFilter() {
    if (!gd) {
      var el = document.querySelector('.plotly-graph-div');
      if (el && el._fullData) { gd = el; } else { return; }
    }
    var traceIndices = [];
    var visibilities = [];
    document.querySelectorAll('.pf-cb').forEach(function (cb) {
      var idx = PID_TO_TRACE[cb.value];
      if (idx !== undefined) {
        traceIndices.push(idx);
        visibilities.push(cb.checked);
      }
    });
    // 一次 restyle 全部，避免多次重繪
    Plotly.restyle(gd, { visible: visibilities }, traceIndices);
  }

  // 綁定所有 checkbox 的 change 事件
  function bindCheckboxes() {
    document.querySelectorAll('.pf-cb').forEach(function (cb) {
      cb.addEventListener('change', applyFilter);
    });
  }

  window.pfSelectAll = function () {
    document.querySelectorAll('.pf-cb').forEach(function (cb) { cb.checked = true; });
    applyFilter();
  };
  window.pfClearAll = function () {
    document.querySelectorAll('.pf-cb').forEach(function (cb) { cb.checked = false; });
    applyFilter();
  };

  bindCheckboxes();
  waitForPlotly();
})();
</script>"""
    )

    with open(output_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_content = html_content.replace('</body>', filter_block + '\n</body>')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return model_poly, df

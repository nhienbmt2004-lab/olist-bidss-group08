"""Create a report figure from the chronological late-delivery forecast evidence."""

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/mysql/forecast_late_delivery'
comparison = pd.read_csv(OUT / 'actionable_comparison.csv')
monthly = pd.read_csv(OUT / 'monthly_metrics.csv')

fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout='constrained')
colors = {'AfterApproval': '#4e79a7', 'AtCarrierHandover': '#e15759'}
for i, cohort in enumerate(['BeforePromise', 'AtLeast3DaysBeforePromise']):
    x = comparison[comparison.Cohort == cohort].set_index('Stage')
    axes[0].bar([i-.17, i+.17],
                [100*x.loc['AfterApproval', 'Top10Capture'],
                 100*x.loc['AtCarrierHandover', 'Top10Capture']],
                width=.32, color=[colors['AfterApproval'], colors['AtCarrierHandover']])
axes[0].axhline(10, linestyle='--', color='#666', linewidth=1, label='Chọn ngẫu nhiên 10%')
axes[0].set_xticks([0, 1], ['Chưa đến hạn', 'Còn ít nhất 3 ngày'])
axes[0].set_ylabel('Tỷ lệ đơn trễ tìm được trong top 10% (%)')
axes[0].set_title('Cảnh báo hai lần trên cùng nhóm đơn')
axes[0].set_ylim(0, 43)
axes[0].bar([2], [0], color=colors['AfterApproval'], label='Lúc duyệt đơn')
axes[0].bar([2], [0], color=colors['AtCarrierHandover'], label='Lúc bàn giao')
axes[0].legend(loc='upper right', fontsize=8)

axes[1].plot(monthly.Month, 100*monthly.Top10Capture, marker='o',
             color='#e15759', linewidth=2, label='Mô hình lúc duyệt')
axes[1].axhline(10, linestyle='--', color='#666', linewidth=1, label='Chọn ngẫu nhiên 10%')
axes[1].set_ylabel('Tỷ lệ đơn trễ tìm được trong top 10% (%)')
axes[1].set_title('Hiệu quả thay đổi theo tháng đặt hàng')
axes[1].set_ylim(0, 47)
axes[1].tick_params(axis='x', labelrotation=35)
axes[1].legend(loc='upper right', fontsize=8)
fig.suptitle('Cảnh báo giao trễ Olist: kiểm thử theo thời gian', fontweight='bold')
fig.savefig(OUT / 'two_stage_temporal_validation.png', dpi=180)
plt.close(fig)
print(OUT / 'two_stage_temporal_validation.png')

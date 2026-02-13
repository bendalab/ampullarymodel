
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from ampullary_ui.plotting.plot_helpers_general import plot_params, colorcode
plt.rcParams.update(plot_params)

from IPython import embed

def plot_samples(values, samples, titles):

    
    fig = plt.figure(figsize=(6, 8))
    gs = GridSpec(34, 47, figure=fig)
    a1 = fig.add_subplot(gs[0:4, 0:7])
    a2 = fig.add_subplot(gs[0:4, 12:19])
    a3 = fig.add_subplot(gs[0:4, 24:31])
    b1 = fig.add_subplot(gs[0:4, 40:47])
    c1 = fig.add_subplot(gs[8:12, 0:7])
    c2 = fig.add_subplot(gs[8:12, 10:17])
    c3 = fig.add_subplot(gs[8:12, 20:27])
    c4 = fig.add_subplot(gs[15:19, 10:17])
    c5 = fig.add_subplot(gs[15:19, 25:32])
    g1 = fig.add_subplot(gs[23:27, 0:7])
    g2 = fig.add_subplot(gs[23:27, 10:17])
    g3 = fig.add_subplot(gs[23:27, 20:27])
    g4 = fig.add_subplot(gs[23:27, 30:37])
    g5 = fig.add_subplot(gs[23:27, 40:47])
    g6 = fig.add_subplot(gs[30:34, 10:17])
    g7 = fig.add_subplot(gs[30:34, 20:27])
    g8 = fig.add_subplot(gs[30:34, 35:42])
    axes = [a1, a2, a3, b1, c1, c2, c3, c4, c5, g1, g2, g3, g4, g5, g6, g7, g8]

    for r in range(len(values)):
        ax = axes[r]
        ax.set_title(titles[r], color=colorcode['highlight'], pad=4)
        x = samples[:,r]
        violin_parts = ax.violinplot(x, positions=[0.0], showmeans=False, showmedians=False,
        showextrema=False, widths=0.4, bw_method=0.2)
        for vp in violin_parts['bodies']:
            vp.set_facecolor(colorcode['standart_blue'])
            vp.set_edgecolor(colorcode['light_blue'])
            vp.set_linewidth(1.0)
            vp.set_alpha(1)
            vp.set_zorder(5)
        if not np.isnan(values[r]):
            ax.plot(0.0, values[r], marker='o', color=colorcode['stimulus'], markersize=5, zorder=10)
        ax.get_xaxis().set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.set_xlim(-0.42, 0.42)
    a1.set_ylabel('Rate [Hz]')
    a2.set_ylabel(r"CV$_{ISI}$ [ms]")
    a3.set_ylabel(r"SC$_{ISI}$ [ms]", labelpad=-2)
    b1.set_ylabel('Rate\nmodulation\n[Hz]')
    c1.set_ylabel('Coherence')
    c4.set_ylabel('Frequency [Hz]')
    g1.set_ylabel(r'Gain [$\frac{Hz}{100\%}$]')
    g6.set_ylabel('Frequency [Hz]')

    le = fig.add_subplot(gs[10:12, 31:])
    le.axis('off')
    if np.isnan(values).all() == False:
        handles = [
            mpatches.Patch(
                facecolor=colorcode['standart_blue'],
                edgecolor=colorcode['light_blue'],         
                linewidth=1.5,
                label=f'Samples (n={len(x)})'),
            Line2D([0], [0], marker='o', color='none',
                markerfacecolor=colorcode['stimulus'],
                markeredgecolor=colorcode['stimulus'],
                markersize=6,label='searched values')]
    else:
            handles = [
        mpatches.Patch(
            facecolor=colorcode['standart_blue'],
            edgecolor=colorcode['light_blue'],         
            linewidth=1.5,
            label=f'Samples (n={len(x)})')]

    le.legend(handles=handles, loc='center', fontsize=9, framealpha=0.0, fancybox=False)
    fig.align_ylabels([a1, c1, g1]) 
    fig.subplots_adjust(left=0.13, right=0.98, top=0.97, bottom=0.05)
    return fig




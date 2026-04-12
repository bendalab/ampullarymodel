"""
Simulate artificial cell 
"""

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.legend_handler import HandlerTuple
from matplotlib.ticker import MultipleLocator
from ampullary_ui.analysis.whitenoise import gain_features, cutoff,values_high_frequencies, is_outlier
from ampullary_ui.plotting.plot_helpers_general import plot_params, colorcode
plt.rcParams.update(plot_params)

dt = 1./20_000  # s  FIXME this should go into a config file or Settings

def plot_cell(base, stim):
    # base.to_pickle(f'baseplot_data_sim.pkl')
    # stim.to_pickle(f'stimplot_data_sim.pkl')

    time = base.membrane_time[0]
    # membrane_voltage = base.membrane_voltage[0]
    spike_times_base = base.spike_times[0]
    lags = base.lags[0]
    corrs = base.corrs[0]
    spike_times = stim.spike_times[0]
    stimulus = stim.stimulus[0]
    stimulus_time = stim.stimulus_time[0]
    rate = stim.conv_rate[0]
    error = stim.conv_std[0]
    freq = stim.tf_f[0]
    tf_smoothed = stim.tf_smoothed[0]
    tf_std = stim.tf_std[0]
    f = stim.stimulus_freq[0]
    Cxy_smoothed = stim.coherence_smooth[0]
    Cxy_std = stim.coherence_std[0]

    # Draw nicer spikes
    membrane_voltage = base.membrane_voltage[0].copy()
    mvmax = np.max(membrane_voltage)
    for spike in spike_times_base:
        i = int(spike / dt)
        membrane_voltage[i] = mvmax*3

    time_length_base = 0.1
    time_length = 0.4
    unit = 'ms'
    factor = 1000

    # fig = plt.figure(figsize=(
    # 14/2.54, 11/2.54))
    plt.close()
    fig = plt.figure(figsize=(5, 5))
    gs = GridSpec(28, 32, figure=fig)
    # baseline fr
    ax1 = fig.add_subplot(gs[:5, :-18])
    ax1.plot(time*factor, membrane_voltage,
             color=colorcode['standart_blue'], label='Voltage')
    ax1.set_ylabel("Voltage [mV]")
    ax1.set_xlabel(f"Time [{unit}]")
    ax1.set_xlim(0.0, time_length_base*factor)
    ax1.set_ylim(np.min(membrane_voltage)-((np.max(membrane_voltage)-np.min(membrane_voltage))/5.0),
                 np.max(membrane_voltage)+((np.max(membrane_voltage)-np.min(membrane_voltage))/10.0))

    # isi
    ax2 = fig.add_subplot(gs[:5, -14:-10])
    isis = np.diff(base.spike_times[0])
    isis = isis[~is_outlier(isis)]
    ax2.hist(isis*1000, 10, color=colorcode['standart_blue'],
             edgecolor=colorcode['light_blue'], linewidth=0.5)
    ax2.set_ylabel("Counts")
    ax2.set_xlabel("ISI [ms]")
    ax2.set_xlim(np.min(isis)*1000 - 1, np.max(isis)*1000 + 1)

    # serial correlation
    ax3 = fig.add_subplot(gs[:5, -6:])
    ax3.hlines(0.0, lags[0], lags[-1],
               color=colorcode['stimulus'],  linewidth=1.0)
    ax3.plot(lags, corrs, '.-',
             color=colorcode['standart_blue'], label='serial\ncorrelations', zorder=2)
    ax3.set_xlabel('Lag')
    ax3.set_ylabel('Correlation')
    ax3.xaxis.set_major_locator(MultipleLocator(5))
    ax3.xaxis.set_major_formatter('{x:.0f}')
    ax3.xaxis.set_minor_locator(MultipleLocator(1))
    ax3.yaxis.set_major_locator(MultipleLocator(0.5))
    ax3.yaxis.set_major_formatter('{x:.1f}')
    ax3.yaxis.set_minor_locator(MultipleLocator(0.1))

    # stimulus
    ax4 = fig.add_subplot(gs[8:10, :25])
    ax4.plot(stimulus_time*factor, stimulus, color=colorcode["stimulus"])
    ax4.set_xlim(0.1*factor, (0.1*factor)+(time_length*factor))
    ax4.get_xaxis().set_visible(False)
    ax4.spines['bottom'].set_visible(False)
    ax4.get_yaxis().set_visible(False)
    ax4.spines['left'].set_visible(False)

    ax_yDist = plt.subplot(gs[8:10, 26:-2], sharey=ax4)
    ax_yDist.hist(stimulus, bins=10, density=True,
                  color=colorcode["stimulus"], edgecolor='#282829', linewidth=0.5, orientation='horizontal', align='mid')
    ax_yDist.set(xlabel='density')
    ax_yDist.get_yaxis().set_visible(False)
    ax_yDist.get_xaxis().set_visible(False)
    ax_yDist.spines['bottom'].set_visible(False)

    # noise response
    ax5 = fig.add_subplot(gs[10:14, :25])
    ax5.plot(stimulus_time*factor, rate, color=colorcode['standart_blue'])
    ax5.fill_between(stimulus_time*factor, rate - error, rate + error,
                     # , alpha=0.4)
                     color=colorcode['light_blue'], alpha=1, label="std")
    trials_ax = ax5.twinx()
    for i in range(len(spike_times)):
        trials_ax.plot(spike_times[i]*1000, np.ones_like(spike_times[i]) * i + 1,
                       marker="|", markersize=2, color=colorcode['standart_blue'], ls="None")
    yax = trials_ax.axes.get_yaxis()
    yax = yax.set_visible(False)
    ax5.sharex(ax4)
    ax5.set_ylabel("Rate [Hz]")
    ax5.set_xlabel(f"Time [{unit}]")
    ax5.set_xlim(0.1*factor, (0.1*factor)+(time_length*factor))
    ax5.set_ylim(0.0, np.ceil(max(rate)/10)*10)

    ax_yDist = plt.subplot(gs[10:14, 26:-2], sharey=ax5)
    ax_yDist.hist(rate, bins=10, density=True, color=colorcode['standart_blue'],
                  edgecolor=colorcode['light_blue'], linewidth=0.5, orientation='horizontal', align='mid')
    ax_yDist.get_yaxis().set_visible(False)
    ax_yDist.get_xaxis().set_visible(False)
    ax_yDist.spines['bottom'].set_visible(False)

    # coherence
    ax6 = fig.add_subplot(gs[19:, :14])
    fcutoff_cxy = cutoff(f, Cxy_smoothed)
    highf_coh = values_high_frequencies(f, Cxy_smoothed, 120.0, 150.0)
    A = ax6.plot(f, Cxy_smoothed,
                 color=colorcode['standart_blue'], label=r'$C_{xy}(f)$')
    B = ax6.fill_between(f, Cxy_smoothed-Cxy_std, Cxy_smoothed +
                         Cxy_std, color=colorcode['light_blue'], alpha=1, label='STD')
    D = ax6.plot([120.0, 150.0], [highf_coh, highf_coh], lw=2.5,
                 color=colorcode['highlight'], label=r'$c_{high_f}$')
    C = ax6.plot(f[0], Cxy_smoothed[0], 'o',
                 color=colorcode['highlight'], label='Features', clip_on=False)
    ax6.plot(f[Cxy_smoothed == np.max(Cxy_smoothed)], np.max(
        Cxy_smoothed), 'o', color=colorcode['highlight'], label=r'$c_{max}$')
    ax6.plot(fcutoff_cxy, np.max(Cxy_smoothed)*0.7071, 'o',
             color=colorcode['highlight'], label=r'$f_{cutoff}$')
    ax6.vlines(fcutoff_cxy, 0.0, Cxy_smoothed[f == fcutoff_cxy][0],
               alpha=0.3, linestyles='dashed', color=colorcode['highlight'])
    ax6.vlines(f[Cxy_smoothed == np.max(Cxy_smoothed)], 0.0, np.max(
        Cxy_smoothed), alpha=0.3, linestyles='dashed', color=colorcode['highlight'])
    ax6.hlines(np.max(Cxy_smoothed), 0.0, f[Cxy_smoothed == np.max(
        Cxy_smoothed)], alpha=0.3, linestyles='dotted', color=colorcode['highlight'])
    ax6.hlines(highf_coh, 0.0, 120.0, alpha=0.3,
               linestyles='dotted', color=colorcode['highlight'])
    ax6.set_xlabel('Frequency [Hz]')
    ax6.set_ylabel('Coherence')
    ax6.set_xlim(0.0, 150.0)
    ax6.set_ylim(0.0, 1.0)
    ticks = [0.0, f[Cxy_smoothed == np.max(
        Cxy_smoothed)][0], fcutoff_cxy, 120, 150]
    ax6.set_xticks(ticks)
    xlabels = [0, ' ', ' ', 120, 150]
    ax6.set_xticklabels(xlabels)
    ax6.xaxis.set_minor_locator(MultipleLocator(10))
    ax6.spines['left'].set_position(('outward', 2))
    ax6.legend(
        [A[0], B, (C[0], D[0])],
        [_.get_label() for _ in [A[0], B, C[0]]],
        handler_map={tuple: HandlerTuple(ndivide=2)},
        framealpha=0.0, fancybox=False, ncol=3, loc='center',  bbox_to_anchor=(0.5, 1.1))

    # transfer function
    ax7 = fig.add_subplot(gs[19:, 18:])
    A = ax7.plot(freq, tf_smoothed,
                 color=colorcode['standart_blue'], label=r'$G_{xy}(f)$')
    B = ax7.fill_between(freq, tf_smoothed-tf_std, tf_smoothed +
                         tf_std, color=colorcode['light_blue'], alpha=1, label='STD')

    gain_0, gain_halfup, f_halfup, max_gain, f_at_gainmax, highf_gain, mfr_gain, fcutoff_up = gain_features(
        freq, tf_smoothed, rate)
    D = ax7.plot([120.0, 150.0], [highf_gain, highf_gain], lw=2.5,
                 color=colorcode['highlight'], label=r'$gain_{high_f}$')
    C = ax7.plot(0.0, gain_0, 'o',
                 color=colorcode['highlight'], label='Features', clip_on=False)
    ax7.plot(f_halfup, gain_halfup, 'o',
             color=colorcode['highlight'], label=r'$gain_{1/2max}$')
    ax7.plot(fcutoff_up, max_gain*0.7071, 'o',
             color=colorcode['highlight'], label=r'$f_{cutoff}$')
    ax7.plot(np.mean(rate), mfr_gain, 'o',
             color=colorcode['highlight'], label=r'$gain_{mean FR}$')
    ax7.plot(f_at_gainmax, max_gain, 'o',
             color=colorcode['highlight'], label=r'$gain_{max}$')
    ax7.vlines(f_halfup, 0.0, gain_halfup,
               color=colorcode['highlight'], alpha=0.3, linestyles='dashed')
    ax7.vlines(f_at_gainmax, 0.0, max_gain,
               color=colorcode['highlight'], alpha=0.3, linestyles='dashed')
    ax7.vlines(fcutoff_up, 0.0, max_gain*0.7071,
               color=colorcode['highlight'], alpha=0.3, linestyles='dashed')
    ax7.hlines(gain_halfup, 0.0, f_halfup,
               color=colorcode['highlight'], alpha=0.3, linestyles='dotted')
    ax7.hlines(max_gain, 0.0, f_at_gainmax,
               color=colorcode['highlight'], alpha=0.3, linestyles='dotted')
    ax7.hlines(mfr_gain, 0.0, np.mean(rate),
               color=colorcode['highlight'], alpha=0.3, linestyles='dotted')
    ax7.hlines(highf_gain, 0.0, 120.0,
               color=colorcode['highlight'], alpha=0.3, linestyles='dotted')
    up = np.ceil((max(tf_smoothed) + max(tf_smoothed)*0.15) / 10.0) * 10
    ax7.set_ylim(0.0, up)
    ax7.set_xlim(0.0, 150.0)
    ticks = [0.0, f_halfup, f_at_gainmax, fcutoff_up,  120, 150]
    ax7.set_xticks(ticks)
    xlabels = [0, ' ', ' ', ' ', 120, 150]

    ax7.set_xticklabels(xlabels)
    ax7.xaxis.set_minor_locator(MultipleLocator(10))
    ax7.spines['left'].set_position(('outward', 2))
    ax7.set_xlabel('Frequency [Hz]')
    ax7.set_ylabel('Gain ' + r'$[\frac{Hz}{100\%}]$')
    ax7.legend(framealpha=0.0, fancybox=False)
    ax7.legend(
        [A[0], B, (C[0], D[0])],
        [_.get_label() for _ in [A[0], B, C[0]]],
        handler_map={tuple: HandlerTuple(ndivide=2)},
        framealpha=0.0, fancybox=False, ncol=3, loc='center',  bbox_to_anchor=(0.5, 1.1))
    fig.align_ylabels([ax1, ax5, ax6])
    fig.subplots_adjust(left=0.1, right=0.98, top=0.97, bottom=0.1)
    return fig

from SSINS import util, INS, MF
from SSINS.match_filter import Event
from SSINS.data import DATA_PATH
import os
import numpy as np
import scipy.stats


def test_obslist():
    obsfile = os.path.join(DATA_PATH, 'test_obs_list.txt')
    outfile = os.path.join(DATA_PATH, 'test_obs_list_out.txt')
    obslist_test = ['1061313008', '1061313128', '1061318864', '1061318984']
    obslist = util.make_obslist(obsfile)
    util.make_obsfile(obslist, outfile)
    obslist_test_2 = util.make_obslist(outfile)

    assert obslist_test == obslist, "The lists were not equal"
    assert os.path.exists(outfile), "A file was not written"
    assert obslist_test == obslist_test_2, "The new file did not read in properly"

    os.remove(outfile)


def test_event_count():

    time_range = np.arange(10)
    freq_range = np.arange(10)
    event_list = [Event(slice(0, 1), slice(2, 3), "narrow_170.000MHz", 10),
                  Event(slice(2, 3), slice(2, 3), "narrow_170.000MHz", 10)]

    assert util.event_count(event_list, time_range) == 2

    event_list.append(Event(slice(0, 11), slice(2, 3), "narrow_170.000MHz", None))

    assert util.event_count(event_list, time_range) == 10


def test_calc_occ():

    obs = "1061313128_99bl_1pol_half_time_SSINS"
    testfile = os.path.join(DATA_PATH, f"{obs}.h5")

    ins = INS(testfile)

    # Mock some flaggable data
    ins.select(freq_chans=np.arange(32), times=ins.time_array[:22])

    ins.metric_array[:] = 1
    ins.weights_array[:] = 10
    ins.weights_square_array[:] = 10
    # Make some outliers
    # Narrowband in 1th, 26th, and 31th frequency
    ins.metric_array[1, 1, :] = 100
    ins.metric_array[1, 30, :] = 100
    ins.metric_array[3:14, 26, :] = 100
    # Arbitrary shape in 2, 3, 4
    ins.metric_array[3:14, 2:25, :] = 100
    ins.metric_array[[0, -1], :, :] = np.ma.masked
    ins.metric_array[:, [0, -1], :] = np.ma.masked
    ins.metric_ms = ins.mean_subtract()

    num_int_flag = 2
    num_chan_flag = 2

    num_init_flag = np.sum(ins.metric_array.mask)

    ch_wid = ins.freq_array[1] - ins.freq_array[0]
    shape_dict = {"shape": [ins.freq_array[2] + 0.1 * ch_wid, ins.freq_array[24] - 0.1 * ch_wid]}
    mf = MF(ins.freq_array, 5, tb_aggro=0.5, shape_dict=shape_dict)
    mf.apply_match_test(ins, time_broadcast=True)

    occ_dict = util.calc_occ(ins, mf, num_init_flag, num_int_flag=2,
                             lump_narrowband=False)
    assert occ_dict["streak"] == 0
    assert occ_dict["narrow_%.3fMHz" % (ins.freq_array[1] * 10**(-6))] == 0.05
    assert occ_dict["narrow_%.3fMHz" % (ins.freq_array[26] * 10**(-6))] == 1
    assert occ_dict["narrow_%.3fMHz" % (ins.freq_array[30] * 10**(-6))] == 0.05
    assert occ_dict["shape"] == 1

    occ_dict = util.calc_occ(ins, mf, num_init_flag, num_int_flag=2,
                             lump_narrowband=True)

    # total narrow over total valid
    assert occ_dict["narrow"] == 24 / 600
    assert occ_dict["streak"] == 0
    assert occ_dict["shape"] == 1
    assert "narrow_%.3fMHz" % (ins.freq_array[1] * 10**(-6)) not in occ_dict.keys()
    assert "narrow_%.3fMHz" % (ins.freq_array[30] * 10**(-6)) not in occ_dict.keys()


def test_make_ticks():

    # Make up a frequency array and some frequencies to tick
    freq_array = np.arange(1e8, 1.1e8, 1e6)
    freqs = np.arange(1e8, 1.1e8, 2e6)

    ticks, labels = util.make_ticks_labels(freqs, freq_array, sig_fig=2)

    test_ticks = (np.arange(len(freq_array))[::2]).tolist()
    test_labels = ['100.00', '102.00', '104.00', '106.00', '108.00']

    assert np.all(ticks == test_ticks), "The ticks are not equal"
    assert np.all(labels == test_labels), "The labels are not equal"

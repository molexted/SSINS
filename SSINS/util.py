"""
Some utility functions. Some are utilized within the main code and some are just
nice to have around.
"""
import numpy as np
import os
from SSINS.match_filter import Event


def event_count(event_list, time_range, freq_range=None):
    shape_set = set()
    for event in event_list:
        if freq_range is None:
            shape_set = shape_set.union(time_range[event.time_slice])
        else:
            ntimes_event = event.time_slice.stop - event.time_slice.start
            event_set = set(zip(time_range[event.time_slice],
                                np.repeat(freq_range[event.freq_slice], ntimes_event)))
            shape_set = shape_set.union(event_set)

    return(len(shape_set))


def calc_occ(ins, mf, num_init_flag, num_int_flag=0, lump_narrowband=False):
    """
    Calculates the fraction of times an event was caught by the flagger for
    each type of event. Does not take care of frequency broadcasted events.

    Args:
        ins: The flagged incoherent noise spectrum in question
        mf: The match filter used to flag the INS
        num_init_flag: The number of initially flagged samples
        num_int_flag: The number of fully flagged integrations in the starting flags
        lump_narrowband: Whether to combine narrowband occupancies into a single number.
            Will slightly overestimate if n_int_flag > 0.

    Returns:
        occ_dict: A dictionary with shapes for keys and occupancy fractions for values
    """
    occ_dict = {shape: 0. for shape in mf.slice_dict}

    # Figure out the total occupancy sans initial flags
    total_data = np.prod(ins.metric_array.shape)
    total_valid = total_data - num_init_flag
    total_flag = np.sum(ins.metric_array.mask)
    total_RFI = total_flag - num_init_flag
    total_occ = total_RFI / total_valid

    init_shapes = list(occ_dict.keys())

    for shape in init_shapes:
        relevant_events = [event for event in ins.match_events if shape in event.shape]
        time_range = np.arange(ins.Ntimes)

        if shape == "narrow":
            if lump_narrowband:
                freq_range = np.arange(ins.Nfreqs)
                # The length of the shape_set tells you how many points were flagged, without overcounting
                occ_dict[shape] = event_count(relevant_events, time_range, freq_range) / total_valid
            else:
                # Need to pull out the unique frequencies that were identified
                new_event_shapes = []
                for event in relevant_events:
                    _ind = event.shape.rfind("_")
                    if event.shape[_ind + 1:] not in new_event_shapes:
                        new_event_shapes.append(event.shape[_ind + 1:])
                # need to iterate over unique frequencies
                for subshape in new_event_shapes:
                    subshape_key = f"narrow_{subshape}"
                    subshape_relevant_events = [event for event in relevant_events if subshape in event.shape]
                    occ_dict[subshape_key] = event_count(subshape_relevant_events,
                                                         time_range) / (ins.Ntimes - num_int_flag)

                    if occ_dict[subshape_key] > 1:
                        occ_dict[subshape_key] = 1
        else:
            occ_dict[shape] = event_count(relevant_events, time_range) / (ins.Ntimes - num_int_flag)
            if occ_dict[shape] > 1:
                occ_dict[shape] = 1

    if not lump_narrowband:
        occ_dict.pop("narrow")

    occ_dict['total'] = total_occ

    return(occ_dict)


def make_obslist(obsfile):
    r"""
    Makes a python list from a text file whose lines are separated by "\\n"

    Args:
        obsfile: A text file with an obsid on each line

    Returns:
        obslist: A list whose entries are obsids
    """
    with open(obsfile) as f:
        obslist = f.read().split("\n")
    while '' in obslist:
        obslist.remove('')
    obslist.sort()
    return(obslist)


def make_obsfile(obslist, outpath):
    """
    Makes a text file from a list of obsids

    Args:
        obslist: A list of obsids
        outpath: The filename to write to
    """
    with open(outpath, 'w') as f:
        for obs in obslist:
            f.write("%s\n" % obs)


def make_ticks_labels(freqs, freq_array, sig_fig=1):
    """
    Makes xticks from desired frequencies to be ticked and the freq_array.

    Args:
        freqs: The desired frequencies to be ticked, in Hz
        freq_array: The frequency array that is to be ticked.
        sig_fig: Precision of the label - number of digits after decimal point (in Mhz)
    """

    # Find the channel numbers closest to each desired frequency
    ticks = np.array([np.argmin(np.abs(freq_array - freq)) for freq in freqs])
    labels = [('%.' + str(sig_fig) + 'f') % (10**-6 * freq) for freq in freqs]

    return(ticks, labels)

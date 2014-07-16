#! /usr/bin/env python

'''
feature_density: calculate density of signals relative to features.


https://github.com/arq5x/bedtools-protocols/blob/master/bedtools.md#
bp3-plot-transcription-factor-occupancy-surrounding-the-transcription-start-site

'''
import ipdb
import sys

from toolshed import reader
from pybedtools import BedTool, Interval

__version__ = '$Revision$'

BEDGRAPH_STRANDS = ('+', '-')
SIGNAL_COLNUM = 5
GROUP_COLNUM = 5
SUMMARY_COLNUM = 7

def feature_density(feature_bed_filename, signal_bedgraph_filename,
                    chromsize_filename, signal_strand, invert_strand,
                    window_size, feature_label, 
                    window_resolution, map_operation, group_operation,
                    verbose):

    feature_bedtool = BedTool(feature_bed_filename)
    signal_bedtool = BedTool(signal_bedgraph_filename)

    signal_stranded_bedtool = add_strand_to_bedgraph(signal_bedtool,
                                                     signal_strand,
                                                     verbose)

    feature_slop = feature_bedtool.slop(b=window_size,
                                        g=chromsize_filename)

    feature_windows = make_windows(feature_slop, window_resolution,
                                   signal_strand, invert_strand, verbose)

    feature_map = make_map(feature_windows,
                           signal_stranded_bedtool,
                           map_operation,
                           verbose)

    feature_grouped = feature_map.groupby(g=GROUP_COLNUM,
                                          c=SUMMARY_COLNUM,
                                          o=group_operation)

    write_table(feature_grouped, feature_label, verbose)

def add_strand_to_bedgraph(bedtool, strand, verbose):

    ''' rewrites bedgraph to bed6 format, adding strand.
    
        Returns:
            BedTool
    '''

    if verbose:
        print >>sys.stderr, ">> adding strand to bedgraph data ..."

    result = []

    for row in bedtool:
        # new fields are: chrom, start, end, name, score, strand
        fs = row.fields

        fields = [fs[0], int(fs[1]), int(fs[2]), '.', fs[3], strand]
        result.append(Interval(*fields))

    return BedTool(result)

def write_table(grouped_bedtool, label, verbose):
    '''
    Print results in tabular format
    '''
    header_fields = ('#pos','signal','label')
    print '\t'.join(header_fields)

    fname = grouped_bedtool.TEMPFILES[-1]
    for row in reader(fname, header=['pos','signal']):
        fields = (row['pos'], row['signal'], label)
        print '\t'.join(fields)

def make_map(windows_bedtool, signal_bedtool, map_operation, verbose):
    ''' 
    Returns:
        BedTool
    '''
    if verbose:
        print >>sys.stderr, ">> making map ... "

    feature_map = windows_bedtool.map(b=signal_bedtool,
                                      c=SIGNAL_COLNUM,
                                      o=map_operation,
                                      s=True,
                                      null=0)
 
    def keyfunc(interval):
        return int(interval.fields[GROUP_COLNUM-1])

    return BedTool(sorted(feature_map, key=keyfunc))

def make_windows(bedtool, window_resolution, signal_strand,
                 invert_strand, verbose):
    ''' 
    Returns:
        BedTool
    '''
    if verbose:
        print >>sys.stderr, ">> making windows ... "

    # select regions from bedtool that have matching strand. have to do
    # this here because make_windows() drops the strand field
    intervals = []

    for interval in bedtool:
        if not invert_strand and interval.strand == signal_strand:
            intervals.append(interval)
        elif invert_strand and interval.strand != signal_strand:
            intervals.append(interval)

    stranded_bedtool = BedTool(intervals)

    # generate the initial set of windows
    windows = BedTool().window_maker(b=stranded_bedtool,
                                     w=window_resolution,
                                     i='srcwinnum')

    # sort by chrom, start and split the 4th field by "_"
    results = []
    for window in windows:
        fs = window.fields

        name, winnum = fs[3].split('_')
        fields = [fs[0], int(fs[1]), int(fs[2]),
                  name, winnum, signal_strand]

        results.append(fields)

    def keyfunc(fs):
        return tuple([fs[0], fs[1]])

    intervals = [Interval(*i) for i in sorted(results, key=keyfunc)]

    return BedTool(intervals)

def parse_options(args):
    from optparse import OptionParser, OptionGroup

    usage = "%prog [OPTION]... FEATURE_BED SIGNAL_BEDGRAPH CHROM_SIZE"
    version = "%%prog %s" % __version__
    description = ("")

    parser = OptionParser(usage=usage, version=version,
                          description=description)

    group = OptionGroup(parser, "Required")

    group.add_option("--signal-strand", action="store", type='str',
        default=None, help="strand for bedgraph signal ('+' or '-') "
                           "(default: %default)")

    parser.add_option_group(group)

    group = OptionGroup(parser, "Variables")

    group.add_option("--invert-strand", action="store_true", 
        default=False, help="invert strand signal match if mismatched " 
                           "(default: %default)")

    group.add_option("--window-size", action="store", type='int',
        default=1000, help="window size (default: %default)")

    group.add_option("--window-resolution", action="store", type='int',
        default=10, help="window resolution (default: %default)")

    group.add_option("--feature-label", action="store", type='str',
        default='label', help="feature label, reported in output"
        " (default: %default)")

    group.add_option("--map-operation", action="store", type='str',
        default='mean', help="map operation"
        " (default: %default)")

    group.add_option("--group-operation", action="store", type='str',
        default='sum', help="group operation"
        " (default: %default)")

    group.add_option("-v", "--verbose", action="store_true",
        default=False, help="verbose output (default: %default)")

    parser.add_option_group(group)

    options, args = parser.parse_args(args)

    if not options.signal_strand:
        parser.error("specify strand for bedgraph")

    if len(args) != 3:
        parser.error("specify 3 required files")

    return options, args

def main(args=sys.argv[1:]):

    options, args = parse_options(args)

    kwargs = {'signal_strand':options.signal_strand,
              'invert_strand':options.invert_strand,
              'window_size':options.window_size,
              'window_resolution':options.window_resolution,
              'feature_label':options.feature_label,
              'map_operation':options.map_operation,
              'group_operation':options.group_operation,
              'verbose':options.verbose}

    feature_bed_filename = args[0]
    signal_bedgraph_filename = args[1]
    chromsize_filename = args[2]

    return feature_density(feature_bed_filename, signal_bedgraph_filename,
                           chromsize_filename, **kwargs)

if __name__ == '__main__':
    sys.exit(main()) 
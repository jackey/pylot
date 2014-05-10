#
#    Copyright (c) 2007-2009 Corey Goldberg (corey@goldb.org)
#    License: GNU GPLv3
#
#    This file is part of Pylot.
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.  See the GNU General Public License 
#    for more details.
#


import glob
import pickle
import sys
import time
from threading import Thread
import corestats
import reportwriter
import config



SMOOTH_TP_GRAPH = config.SMOOTH_TP_GRAPH  # smooth/dampen the throughput graph based on an interval.  default is 3 secs



def generate_results(dir, test_name):
    print '\nGenerating Results...'
    try:
        merged_log = open(dir + '/agent_stats.csv', 'rb').readlines()  # this log contains commingled results from all agents
    except IOError:
        sys.stderr.write('ERROR: Can not find your results log file\n')
    merged_error_log = merge_error_files(dir)
    
    if len(merged_log) == 0:
        fh = open(dir + '/results.html', 'w')
        fh.write(r'<html><body><p>None of the agents finished successfully.  There is no data to report.</p></body></html>\n')
        fh.close()
        sys.stdout.write('ERROR: None of the agents finished successfully.  There is no data to report.\n')
        return

    timings = list_timings(merged_log)
    best_times, worst_times = best_and_worst_requests(merged_log)
    timer_group_stats = get_timer_groups(merged_log)
    timing_secs = [int(x[0]) for x in timings]  # grab just the secs (rounded-down)
    throughputs = calc_throughputs(timing_secs)  # dict of secs and throughputs
    throughput_stats = corestats.Stats(throughputs.values())
    resp_data_set = [x[1] for x in timings] # grab just the timings
    response_stats = corestats.Stats(resp_data_set)
    
    # calc the stats and load up a dictionary with the results
    stats_dict = get_stats(response_stats, throughput_stats)
    
    # get the pickled stats dictionaries we saved
    runtime_stats_dict, workload_dict = load_dat_detail(dir)
    
    # get the summary stats and load up a dictionary with the results   
    summary_dict = {}
    summary_dict['cur_time'] = time.strftime('%m/%d/%Y %H:%M:%S', time.localtime())
    summary_dict['duration'] = int(timings[-1][0] - timings[0][0]) + 1  # add 1 to round up
    summary_dict['num_agents'] = workload_dict['num_agents']
    summary_dict['req_count'] = len(timing_secs)
    summary_dict['err_count'] = len(merged_error_log)
    summary_dict['bytes_received'] = calc_bytes(merged_log)

    # write html report
    fh = open(dir + '/results.html', 'w')
    reportwriter.write_head_html(fh)
    reportwriter.write_starting_content(fh, test_name)
    reportwriter.write_summary_results(fh, summary_dict, workload_dict)
    reportwriter.write_stats_tables(fh, stats_dict)
    reportwriter.write_images(fh)
    reportwriter.write_timer_group_stats(fh, timer_group_stats)
    reportwriter.write_agent_detail_table(fh, runtime_stats_dict)
    reportwriter.write_best_worst_requests(fh, best_times, worst_times)
    reportwriter.write_closing_html(fh)
    fh.close()
    
    try:  # graphing only works on systems with Matplotlib installed
        print 'Generating Graphs...'
        import graph
        graph.resp_graph(timings, dir=dir+'/')
        graph.tp_graph(throughputs, dir=dir+'/')
    except: 
        sys.stderr.write('ERROR: Unable to generate graphs with Matplotlib\n')
    
    print '\nDone generating results. You can view your test at:'
    print '%s/results.html\n' % dir


def load_dat_detail(dir):
    fh = open(dir + '/agent_detail.dat', 'r')
    runtime_stats = pickle.load(fh)
    fh.close()
    fh = open(dir + '/workload_detail.dat', 'r')
    workload = pickle.load(fh)
    fh.close()
    return (runtime_stats, workload)
        

def merge_error_files(dir):
    merged_file = []    
    for filename in glob.glob(dir + r'/*errors.log'):
        fh = open(filename, 'rb')
        merged_file += fh.readlines()
        fh.close()
    return merged_file
    
    
def list_timings(merged_log):
    # create a list of tuples with our timing data sorted by second
    timings = []
    for line in merged_log:
        splat = line.split(',')
        timing_sec = splat[3].strip()
        response_time = splat[8].strip()
        timings.append((float(timing_sec), float(response_time)))
    return sorted(timings)
    
    
def calc_bytes(merged_log):
    # get total bytes received
    bytes_seq = []
    for line in merged_log:
        bytes = int(line.split(',')[7].strip())
        bytes_seq.append(bytes)
    total_bytes = sum(bytes_seq)
    return total_bytes
    

def calc_throughputs(timing_secs):
    # load up a dictionary with secs as keys and counts as values   
    # need start and end times
    start_sec = timing_secs[0]
    end_sec = timing_secs[-1]
    throughputs = {}
    
    # original implementation with no smoothing
    #for sec in range(start_sec, end_sec + 1):
    #    count = timing_secs.count(sec)       
    #    throughputs[sec - start_sec] = count
    
    # new implementation with smoothing
    cur = start_sec - 1
    step = config.SMOOTH_TP_GRAPH
    for sec in timing_secs:
        if sec > cur:
            cur += step
        k = cur - start_sec - step + 1
        v = throughputs.setdefault(k, 0)
        throughputs[k] += 1
    for k in throughputs:
        throughputs[k] /= float(step)
        
    return throughputs
    

def get_stats(response_stats, throughput_stats):
    stats_dict = {}
    stats_dict['response_avg'] = response_stats.avg()
    stats_dict['response_stdev'] = response_stats.stdev()
    stats_dict['response_min'] = response_stats.min()
    stats_dict['response_max'] = response_stats.max()
    stats_dict['response_50pct'] = response_stats.percentile(50)
    stats_dict['response_80pct'] = response_stats.percentile(80)
    stats_dict['response_90pct'] = response_stats.percentile(90)
    stats_dict['response_95pct'] = response_stats.percentile(95)
    stats_dict['response_99pct'] = response_stats.percentile(99)
    stats_dict['throughput_avg'] = throughput_stats.avg()
    stats_dict['throughput_stdev'] = throughput_stats.stdev()
    stats_dict['throughput_min'] = throughput_stats.min()
    stats_dict['throughput_max'] = throughput_stats.max()
    stats_dict['throughput_50pct'] = throughput_stats.percentile(50)
    stats_dict['throughput_80pct'] = throughput_stats.percentile(80)
    stats_dict['throughput_90pct'] = throughput_stats.percentile(90)
    stats_dict['throughput_95pct'] = throughput_stats.percentile(95)
    stats_dict['throughput_99pct'] = throughput_stats.percentile(99)
    return stats_dict 
    

def get_timer_groups(merged_log):  # get the stats by timer group
    stats_lists = [line.split(',') for line in merged_log]
    uniq_timer_groups = list(set((stats_list[10].strip() for stats_list in stats_lists)))
    timer_group_stats = {}
    for timer_group in uniq_timer_groups:
        elapsed_times = []
        for stat_list in stats_lists:
            if timer_group == stat_list[10].strip():
                if stat_list[5] == '200':  # just concerned with valid responses
                    elapsed_times.append(stat_list[8])
        stats = corestats.Stats(elapsed_times)
        stat_group = [
            stats.count(),
            stats.avg(), 
            stats.stdev(),
            stats.min(), 
            stats.percentile(50), 
            stats.percentile(80), 
            stats.percentile(90), 
            stats.percentile(95), 
            stats.percentile(99), 
            stats.max()
        ]
        timer_group_stats[timer_group] = stat_group
    return timer_group_stats

    
def best_and_worst_requests(merged_log):  # get the fastest/slowest urls
    stats_lists = [line.split(',') for line in merged_log]
    uniq_urls = list(set((stats_list[4] for stats_list in stats_lists)))
    url_times = {}
    for url in uniq_urls:
        total_time = 0.0
        elapsed_times = []
        for stats in stats_lists:
            if url == stats[4]:
                if stats[5] == '200':  # just concerned with valid responses
                    elapsed_times.append(stats[8])
        for elapsed_time in elapsed_times:
            total_time += float(elapsed_time)
            average_time = (total_time / len(elapsed_times))
            url_times[url] = average_time
    raw_times = sorted(url_times.values())
    best_times = {}
    worst_times = {}
    for x in url_times:
        if url_times[x] in raw_times[:3]:  # take the top 3
           best_times[x] = url_times[x]
    for x in url_times:
        if url_times[x] in raw_times[-3:]:  # take the bottom 3
           worst_times[x] = url_times[x]
    return (best_times, worst_times)




class ResultsGenerator(Thread):  # generate results in a new thread so UI isn't blocked
    def __init__(self, dir, test_name):
        Thread.__init__(self)
        self.dir = dir
        self.test_name = test_name
        
    def run(self):
        try:
            generate_results(self.dir, self.test_name)
        except Exception, e:
            sys.stderr.write('ERROR: Unable to generate results: %s\n' % e)
        
        
            

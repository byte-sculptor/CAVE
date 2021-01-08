from cave.cavefacade import CAVE


cave = CAVE(
    folders=[r"N:\MLOS\LocklessQueue\cave_reports_v2\gen5_run"],
    output_dir=r"N:\MLOS\LocklessQueue\cave_reports_v2\cave_reports",
    ta_exec_dir=[r"N:\MLOS\LocklessQueue\cave_reports_v2\gen5_run"],
    file_format="CSV"
)

#cave.analyze(
#    performance=True,
#    cdf=False,
#    scatter=False,
#    cfp=False,
#    cfp_time_slider=False,
#    cfp_max_plot=-1,
#    cfp_number_quantiles=10,
#    param_importance=['lpi', 'fanova'],
#    pimp_sort_table_by="average",
#    feature_analysis=["box_violin", "correlation", "importance", "clustering", "feature_cdf"],
#    parallel_coordinates=False,
#    cost_over_time=False,
#    cot_inc_traj='racing',
#    algo_footprint=False
#)

cave.analyze(
    performance=True,
    cdf=True,
    scatter=True,
    cfp=True,
    cfp_time_slider=True,
    cfp_max_plot=-1,
    cfp_number_quantiles=10,
    param_importance=['lpi', 'fanova', 'ablation', 'forward_selection'],
    pimp_sort_table_by="average",
    feature_analysis=["box_violin", "correlation", "importance", "clustering", "feature_cdf"],
    parallel_coordinates=True,
    cost_over_time=True,
    cot_inc_traj='racing',
    algo_footprint=True
)

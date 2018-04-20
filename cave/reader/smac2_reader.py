import re
import os
import shutil
import csv
import numpy as np
import pandas as pd

from ConfigSpace import Configuration, c_util
from ConfigSpace.hyperparameters import IntegerHyperparameter, FloatHyperparameter
from ConfigSpace.util import deactivate_inactive_hyperparameters, fix_types
from smac.optimizer.objective import average_cost
from smac.utils.io.input_reader import InputReader
from smac.runhistory.runhistory import RunKey, RunValue, RunHistory, DataOrigin
from smac.utils.io.traj_logging import TrajLogger
from smac.scenario.scenario import Scenario

from cave.reader.base_reader import BaseReader, changedir
from cave.reader.csv2rh import CSV2RH
from cave.utils.io import load_csv_to_pandaframe

class SMAC2Reader(BaseReader):

    def get_scenario(self):
        run_1_existed = os.path.exists('run_1')
        in_reader = InputReader()
        # Create Scenario (disable output_dir to avoid cluttering)
        scen_fn = os.path.join(self.folder, 'scenario.txt')
        scen_dict = in_reader.read_scenario_file(scen_fn)
        scen_dict['output_dir'] = ""
        with changedir(self.ta_exec_dir):
            self.logger.debug("Creating scenario from \"%s\"", self.ta_exec_dir)
            scen = Scenario(scen_dict)

        if (not run_1_existed) and os.path.exists('run_1'):
            shutil.rmtree('run_1')
        self.scen = scen
        return scen

    def get_runhistory(self, cs):
        """
        Expects the following files:

        - `self.folder/runs_and_results(...).csv`
        - `self.folder/paramstrings(...).csv`

        Returns
        -------
        (rh, validated_rh): RunHistory, Union[False, RunHistory]
            runhistory and (if available) validated runhistory
        """

        validated_rh = False
        rh_fn = re.search(r'runs\_and\_results.*?\.csv', str(os.listdir(self.folder)))
        if not rh_fn:
            raise FileNotFoundError("Specified format is \'SMAC2\', but no "
                                    "\'runs_and_results\'-file could be found "
                                    "in %s" % self.folder)
        rh_fn = os.path.join(self.folder, rh_fn.group())
        self.logger.debug("Runhistory loaded as csv from %s", rh_fn)
        configs_fn = re.search(r'paramstrings.*?\.txt', str(os.listdir(self.folder)))
        if not configs_fn:
            raise FileNotFoundError("Specified format is \'SMAC2\', but no "
                                    "\'paramstrings\'-file could be found "
                                    "in %s" % self.folder)
        configs_fn = os.path.join(self.folder, configs_fn.group())
        self.logger.debug("Configurations loaded from %s", configs_fn)
        # Translate smac2 to csv
        csv_data = load_csv_to_pandaframe(rh_fn, self.logger)
        data = pd.DataFrame()
        data["config_id"] = csv_data["Run History Configuration ID"]
        data["instance_id"] = csv_data["Instance ID"].apply(lambda x:
                self.scen.train_insts[x-1])
        data["seed"] = csv_data["Seed"]
        data["time"] = csv_data["Runtime"]
        if self.scen.run_obj == 'runtime':
            data["cost"] = csv_data["Runtime"]
        else:
            data["cost"] = csv_data["Run Quality"]
        data["status"] = csv_data["Run Result"]

        # Load configurations
        with open(configs_fn, 'r') as csv_file:
            csv_data = list(csv.reader(csv_file, delimiter=',',
                                       skipinitialspace=True))
        id_to_config = {}
        for row in csv_data:
            config_id = int(re.match(r'^(\d*):', row[0]).group(1))
            params = [re.match(r'^\d*: (.*)', row[0]).group(1)]
            params.extend(row[1:])
            #self.logger.debug(params)
            matches = [re.match(r'(.*)=\'(.*)\'', p) for p in params]
            values = {m.group(1) : m.group(2) for m in matches}
            values = deactivate_inactive_hyperparameters(fix_types(values, cs),
                                                         cs).get_dictionary()
            id_to_config[config_id] = Configuration(cs, values=values)
        self.id_to_config = id_to_config
        names, feats = self.scen.feature_names, self.scen.feature_dict
        rh = CSV2RH().read_csv_to_rh(data,
                                     cs=cs,
                                     id_to_config=id_to_config,
                                     train_inst=self.scen.train_insts,
                                     test_inst=self.scen.test_insts,
                                     instance_features=feats)

        return (rh, validated_rh)

    def get_trajectory(self, cs):
        """Expects the following files:

        - `self.folder/traj-run-(...).csv`
        """
        traj_fn = re.search(r'traj-run-\d*.txt', str(os.listdir(os.path.join(self.folder, '..'))))
        if not traj_fn:
            raise FileNotFoundError("Specified format is \'SMAC2\', but no "
                                    "\'../traj-run\'-file could be found "
                                    "in %s" % self.folder)
        traj_fn = os.path.join(self.folder, '..', traj_fn.group())
        with open(traj_fn, 'r') as csv_file:
            csv_data = list(csv.reader(csv_file, delimiter=',',
                                       skipinitialspace=True))
        header, csv_data = csv_data[0][:-1], np.array([csv_data[1:]])[0]
        csv_data = pd.DataFrame(np.delete(csv_data, np.s_[5:], axis=1), columns=header)
        csv_data = csv_data.apply(pd.to_numeric, errors='ignore')
        traj = []
        def add_to_traj(row):
            new_entry = {}
            new_entry['cpu_time'] = row['CPU Time Used']
            new_entry['total_cpu_time'] = None
            new_entry["wallclock_time"] = row['Wallclock Time']
            new_entry["evaluations"] = -1
            new_entry["cost"] = row["Estimated Training Performance"]
            new_entry["incumbent"] = self.id_to_config[row["Incumbent ID"]]
            traj.append(new_entry)
        csv_data.apply(add_to_traj, axis=1)
        return traj


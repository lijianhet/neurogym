#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 13:48:19 2019

@author: molano


Perceptual decision-making task, based on

  Bounded integration in parietal cortex underlies decisions even when viewing
  duration is dictated by the environment.
  R Kiani, TD Hanks, & MN Shadlen, JNS 2008.

  http://dx.doi.org/10.1523/JNEUROSCI.4761-07.2008

"""
from __future__ import division

import numpy as np
from gym import spaces
import tasktools
import ngym


class RDM(ngym.ngym):
    # Inputs
    inputs = tasktools.to_map('FIXATION', 'LEFT', 'RIGHT')

    # Actions
    actions = tasktools.to_map('FIXATE', 'CHOOSE-LEFT', 'CHOOSE-RIGHT')

    # Trial conditions
    left_rights = [-1, 1]
    cohs = [0, 6.4, 12.8, 25.6, 51.2]  # Easier: [25.6, 51.2, 102.4, 204.8]

    # Input noise
    sigma = np.sqrt(2*100*0.01)

    # Durations
    fixation = 750
    stimulus_min = 80
    stimulus_mean = 330
    stimulus_max = 1500
    decision = 500
    tmax = fixation + stimulus_max + decision

    # Rewards
    R_ABORTED = -1.
    R_CORRECT = +1.
    R_FAIL = 0.
    R_MISS = 0.

    def __init__(self, dt=100):
        super().__init__(dt=dt)
        self.stimulus_min = np.max([self.stimulus_min, dt])
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(3, ),
                                            dtype=np.float32)

        self.seed()
        self.viewer = None

        self.steps_beyond_done = None

        self.trial = self._new_trial(self.rng, self.dt)
        print('------------------------')
        print('RDM task')
        print('------------------------')

    def _new_trial(self, rng, dt, context={}):
        # ---------------------------------------------------------------------
        # Epochs
        # ---------------------------------------------------------------------

        stimulus = context.get('stimulus')
        if stimulus is None:
            stimulus = tasktools.truncated_exponential(rng, dt,
                                                       self.stimulus_mean,
                                                       xmin=self.stimulus_min,
                                                       xmax=self.stimulus_max)

        durations = {
            'fixation':  (0, self.fixation),
            'stimulus':  (self.fixation, self.fixation + stimulus),
            'decision':  (self.fixation + stimulus,
                          self.fixation + stimulus + self.decision),
            'tmax':      self.tmax
            }
        time, epochs = tasktools.get_epochs_idx(dt, durations)

        # ---------------------------------------------------------------------
        # Trial
        # ---------------------------------------------------------------------

        left_right = context.get('left_right')
        if left_right is None:
            left_right = rng.choice(self.left_rights)

        coh = context.get('coh')
        if coh is None:
            coh = rng.choice(self.cohs)

        return {
            'durations':   durations,
            'time':        time,
            'epochs':      epochs,
            'left_right':  left_right,
            'coh':         coh
            }

    # Input scaling
    def scale(self, coh):
        return (1 + coh/100)/2

    def step(self, action):
        # ---------------------------------------------------------------------
        # Reward
        # ---------------------------------------------------------------------
        trial = self.trial
        epochs = trial['epochs']
        status = {'continue': True}
        reward = 0
        if self.t-1 not in epochs['decision']:
            if action != self.actions['FIXATE']:
                status['continue'] = False
                reward = self.R_ABORTED
        elif self.t-1 in epochs['decision']:
            if action == self.actions['CHOOSE-LEFT']:
                status['continue'] = False
                status['choice'] = 'L'
                status['t_choice'] = self.t-1
                status['correct'] = (trial['left_right'] < 0)
                if status['correct']:
                    reward = self.R_CORRECT
                else:
                    reward = self.R_FAIL
            elif action == self.actions['CHOOSE-RIGHT']:
                status['continue'] = False
                status['choice'] = 'R'
                status['t_choice'] = self.t-1
                status['correct'] = (trial['left_right'] > 0)
                if status['correct']:
                    reward = self.R_CORRECT
                else:
                    reward = self.R_FAIL
        # ---------------------------------------------------------------------
        # Inputs
        # ---------------------------------------------------------------------

        if trial['left_right'] < 0:
            high = self.inputs['LEFT']
            low = self.inputs['RIGHT']
        else:
            high = self.inputs['RIGHT']
            low = self.inputs['LEFT']

        obs = np.zeros(len(self.inputs))
        if self.t in epochs['fixation'] or self.t in epochs['stimulus']:
            obs[self.inputs['FIXATION']] = 1
        if self.t in epochs['stimulus']:
            obs[high] = self.scale(+trial['coh']) +\
                self.rng.normal(scale=self.sigma)/np.sqrt(self.dt)
            obs[low] = self.scale(-trial['coh']) +\
                self.rng.normal(scale=self.sigma)/np.sqrt(self.dt)

        # ---------------------------------------------------------------------
        # new trial?
        reward, new_trial, self.t, self.perf, self.num_tr =\
            tasktools.new_trial(self.t, self.tmax, self.dt, status['continue'],
                                self.R_MISS, self.num_tr, self.perf, reward,
                                self.p_stp)

        if new_trial:
            self.trial = self._new_trial(self.rng, self.dt)

        done = False  # TODO: revisit
        return obs, reward, done, status

    def terminate(perf):
        p_decision, p_correct = tasktools.correct_2AFC(perf)

        return p_decision >= 0.99 and p_correct >= 0.8

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import division

import numpy as np
from gym import spaces

import neurogym as ngym


class DelayedMatchCategory(ngym.PeriodEnv):
    r"""Delayed match-to-category task.

    A sample stimulus is followed by a delay and test. Agents are required
    to indicate if the sample and test are in the same category.
    """
    metadata = {
        'paper_link': 'https://www.nature.com/articles/nature05078',
        'paper_name': '''Experience-dependent representation
        of visual categories in parietal cortex''',
        'tags': ['perceptual', 'working memory', 'two-alternative',
                 'supervised']
    }

    def __init__(self, dt=100, rewards=None, timing=None, sigma=1.5):
        super().__init__(dt=dt)
        self.choices = [1, 2]  # match, non-match

        self.sigma = sigma / np.sqrt(self.dt)  # Input noise

        # Rewards
        self.rewards = {'abort': -0.1, 'correct': +1., 'fail': 0.}
        if rewards:
            self.rewards.update(rewards)

        self.timing = {
            'fixation': ('constant', 500),
            'sample': ('constant', 650),
            'first_delay': ('constant', 1000),
            'test': ('constant', 650)}
        # 'second_delay': ('constant', 250),  # TODO: not implemented
        # 'decision': ('constant', 650)},  # TODO: not implemented}
        if timing:
            self.timing.update(timing)

        self.abort = False

        # Fixation + Match + Non-match
        self.action_space = spaces.Discrete(3)
        self.act_dict = {'fixation': 0, 'match': 1, 'non-match': 2}

        # Fixation + cos(theta) + sin(theta)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(3,),
                                            dtype=np.float32)
        self.ob_dict = {'fixation': 0, 'stimulus': range(1, 3)}


    def new_trial(self, **kwargs):
        """
        new_trial() is called when a trial ends to generate the next trial.
        The following variables are created:
            ground truth: correct response for the trial
            coh: stimulus coherence (evidence) for the trial
            ob: observation
        """
        # ---------------------------------------------------------------------
        # Trial
        # ---------------------------------------------------------------------
        self.trial = {
            'ground_truth': self.rng.choice(self.choices),
            'sample_category': self.rng.choice([0, 1]),
        }
        self.trial.update(**kwargs)

        ground_truth = self.trial['ground_truth']
        sample_category = self.trial['sample_category']

        sample_theta = (sample_category + self.rng.random()) * np.pi

        test_category = sample_category
        if ground_truth == 2:
            test_category = 1 - test_category
        test_theta = (test_category + self.rng.random()) * np.pi
        stim_sample = [np.cos(sample_theta), np.sin(sample_theta)]
        stim_test = [np.cos(test_theta), np.sin(test_theta)]

        # ---------------------------------------------------------------------
        # Periods
        # ---------------------------------------------------------------------
        periods = ['fixation', 'sample', 'first_delay', 'test']
        self.add_period(periods, after=0, last_period=True)
        # self.add_period('decision', after='test', last_period=True)

        self.add_ob(1, where='fixation')
        self.add_ob(stim_sample, 'sample', where='stimulus')
        self.add_ob(stim_test, 'test', where='stimulus')
        self.add_randn(0, self.sigma, 'sample')
        self.add_randn(0, self.sigma, 'test')

        self.set_groundtruth(ground_truth, 'test')

    def _step(self, action, **kwargs):
        """
        _step receives an action and returns:
            a new observation, obs
            reward associated with the action, reward
            a boolean variable indicating whether the experiment has end, done
            a dictionary with extra information:
                ground truth correct response, info['gt']
                boolean indicating the end of the trial, info['new_trial']
        """
        # ---------------------------------------------------------------------
        # Reward and observations
        # ---------------------------------------------------------------------
        new_trial = False

        obs = self.ob_now
        gt = self.gt_now

        reward = 0
        if self.in_period('fixation'):
            if action != 0:
                new_trial = self.abort
                reward = self.rewards['abort']
        elif self.in_period('test'):
            if action != 0:
                new_trial = True
                if action == gt:
                    reward = self.rewards['correct']
                    self.performance = 1
                else:
                    reward = self.rewards['fail']

        return obs, reward, False, {'new_trial': new_trial, 'gt': gt}


if __name__ == '__main__':
    env = DelayedMatchCategory()
    ngym.utils.plot_env(env, num_steps=100)
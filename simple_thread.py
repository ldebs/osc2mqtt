"""
This module provides a simple threading utility for running a function in 
an infinite loop within a separate thread.
"""
import threading
import logging
from typing import Iterable


class SimpleThread:
    """
    A class to create and manage a simple thread that runs a given function in 
    an infinite loop.
    """

    def __init__(self, loop: callable, args: Iterable, autostart=True):
        """
        Initializes a SimpleThread instance.

        Args:
            loop (callable): The function to be executed in the thread.
            args (Iterable): A list of arguments to pass to the loop function.
            autostart (bool, optional): If True, the thread will start automatically upon initialization. Defaults to True.
        """
        self.loop = loop
        self.args = args
        self.alive = False
        if autostart:
            self.start()

    def start(self):
        """
        Call the 'loop' function in an infinite loop in separate thread. The thread will continue to run 
        until the stop method is called.
        """

        def _run(self):
            while self.alive:
                self.loop(*self.args)
        self.alive = True
        self.thread = threading.Thread(target=_run, args=(self,))
        self.thread.start()

    def stop(self):
        """
        Stops and waits for the thread to finish.
        """
        self.alive = False
        self.thread.join()
        logging.info("Thread %s stopped.", self.loop.__name__)

import subprocess
import time
from cas_agent import CasConsoleAgent,CasWorkerAgent,CasBaseAgent,AgentMessage,EdgeBaseAgent

import threading
import sys, os



"""
class TestAgent(CasWorkerAgent):

    def __init__(self, name):
        print("+------------+")
        print("| Test Agent |")
        print("+------------+")
        #EdgeBaseAgent.__init__(self, name, auto_load=False)
        CasWorkerAgent.__init__(self, name, __file__,auto_load=True)
"""

if __name__ == "__main__":
    #watch("./settings","txt")
    #watch()
    agt=CasConsoleAgent(__file__)

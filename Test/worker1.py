from cas_agent import CasConsoleAgent,CasWorkerAgent,CasBaseAgent,AgentMessage
import sys, time

class WorkerZero(CasWorkerAgent):
    ACTIONS = {
        'echo' : 'echo_arg'
    }
    def echo_arg(self,msg:AgentMessage):
        print(msg.Args)

if __name__ == "__main__":
    agt = WorkerZero("worker1",__file__,dir_path="/setting")
    while True:
        time.sleep(1)





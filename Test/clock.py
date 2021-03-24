from cas_agent import CasConsoleAgent,CasWorkerAgent,CasBaseAgent,AgentMessage
import sys, time

class WorkerZero(CasWorkerAgent):
    ACTIONS = {
        'echo' : 'echo_arg'
    }
    def echo_arg(self,msg:AgentMessage):
        print(msg.Args)

if __name__ == "__main__":
    agt = WorkerZero("Clock_agent",__file__,dir_path="/setting")
    msg = AgentMessage()
    msg.To = "ALL"
    msg.From = "test"
    msg.Action = "echo"
    seq=0
    while True:
        time.sleep(1)
        msg.Args = {"seq":seq}
        agt.send_message(msg, qos=0)
        seq+=1




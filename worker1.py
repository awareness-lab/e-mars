from cas_agent import CasConsoleAgent,CasWorkerAgent,CasBaseAgent,AgentMessage
import sys,time
class WorkerOne(CasWorkerAgent):
    ACTIONS = {
        'echo' : 'echo_arg'
    }
    def echo_arg(self,msg:AgentMessage):
        print(msg.Args)

if __name__ == "__main__":
    agt = WorkerOne("worker2",__file__,dir_path="/setting_1")
    msg = AgentMessage()
    msg.To = agt.name
    msg.From = "test"
    msg.Action = "echo"
    seq=0
    while True:
        time.sleep(1)
        msg.Args = {"seq":seq}
        agt.send_message(msg, qos=0)
        seq+=1
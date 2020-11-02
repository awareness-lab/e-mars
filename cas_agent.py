# -*- coding: utf-8 -*-

# Agent
import ssl, configparser, redis, threading, time, sys, os

#AgentMessage
import calendar, datetime, json

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AgentMessage:
    """
    エージェントメッセージ構成クラス
    """
    def __init__(self, json_text=None):
        self.Name = ""
        self.Type = "INFORM"
        self.Date = 0
        self.From = ""
        self.To = ""
        self.Action = ""
        self.Args = None
        self.Contents = None
        self.ContentLanguage = ""
        self.ErrorContents = ""
        self.Timeout = ""
        self.TimeLimit = ""
        self.Ack = ""
        self.Protocol = ""
        self.Strategy = ""
        self.ButFor = ""
        self.TaskID = ""
        self.ReplyTo = ""
        self.RepeatCount = ""
        self.TaskTimeout = ""
        self.SenderIP = ""
        self.SenderSite = ""
        self.Thru = ""

        if json_text is not None:
            self.parse(json_text)

    def to_json(self):
        self.Date = self.generate_unix_time()
        
        # Output Filter
        f = ['Type', 'Date', 'From', 'To', 'Action', 'Args', 'Contents']
        d = {k : v for k, v in filter(lambda t: t[0] in f, self.__dict__.items())} # [TODO]
        return json.dumps(d)
    
    def validate(self):
        pass

    def generate_unix_time(self):
        now = datetime.datetime.utcnow()
        ut = calendar.timegm(now.utctimetuple())
        return ut

    def parse(self, json_text):
        j = json.loads(json_text)
        for k, v in j.items():
            self.__dict__[k] = v

class EdgeBaseAgent:
    # Agent Actions
    ACTIONS = {
        # 'TEST' : 'act_debug'
    }

    def load_settings(self):
        # Coterie設定の読み込み
        config = configparser.ConfigParser()
        config.read('edge_settings.ini')

        self.coterie = config['SETTINGS']['CoterieName']
        self.host = config['SETTINGS']['BrokerIP']
        self.topic = 'coterie-' + self.coterie

        print("[LOG]", "Load Settings : Coterie - ", self.coterie)

    def connect(self):
        self.port = 6379    #Redisのインストール時にポート番号が指定される
        self.blackboard = redis.StrictRedis(host=self.host, port=self.port, db=0)

        # 待ち受け状態にする
        pubsub = self.blackboard.pubsub()
        pubsub.psubscribe(**{self.topic: self.on_message})
        self.thread = pubsub.run_in_thread(sleep_time=0.01)

        self.on_connect()
        print("[LOG] Network Access - OK")

    def reconnect(self):
        self.connect()

    def __init__(self, name, auto_load=True, local=True):
        # エージェントの初期化
        self.name = name
        self.load_settings()
        self.local = local

        if auto_load:
            self.start()


    def start(self):
        self.connect()
        self.initialize()
        self.initialized()


    def stop(self):
        self.thread.stop()


    def on_connect(self):
        print('[LOG] COTERIE status {0}'.format(0))

        msg = AgentMessage()
        msg.Type = "INFORM"
        msg.From = self.name
        msg.To = "ALL"
        msg.Action = "HELLO"
        msg.Args = "HELLO"
        self.send_message(msg)

    def on_message(self, msg):
        # AgentMessage型にパース
        data = msg['data'].decode() #msg.payload.decode("utf-8")
        agt_msg = AgentMessage(data)

        if agt_msg.To in (self.name, "ALL") and agt_msg.From != self.name:
            self.receive_message(agt_msg)

    def send_message(self, msg: AgentMessage, qos=2):
        self.blackboard.publish(self.topic, msg.to_json())

    """
    for override
    """
    def receive_message(self, msg: AgentMessage):
        # print("[DEBUG-NEW]", msg.to_json())
        if msg.Action in self.ACTIONS:
            action_name = self.ACTIONS[msg.Action]
            try:
                method = getattr(self, action_name)
            except AttributeError:
                print("[ERROR]", action_name, "is nothing.")
            method(msg)

    def initialize(self):
        pass

    def initialized(self):
        pass

    # --- Properties ---
    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

class MyHandler(FileSystemEventHandler):
    flag = True
    def _run_command(self):
        print("Detect file event")
        MyHandler.flag = False

    def on_moved(self, event):
        self._run_command()

    def on_created(self, event):
        self._run_command()

    def on_deleted(self, event):
        self._run_command()

    def on_modified(self, event):
        self._run_command()

class CasBaseAgent(EdgeBaseAgent):
    def __init__(self, name, file_name, auto_load=True, local=True, coterie="Experiment", host="127.0.0.1"):
        # load_settings廃止 設定ハードコーディング
        self.name = name
        self.coterie = coterie
        self.host = host
        self.topic = 'coterie-' + self.coterie
        self.local = local
        self.status = "Alive"

        self.file_name=file_name

        print("[LOG] "+self.name+" started.")

        if auto_load:
            self.start()

        # マネジメント用のスレッド設定＆開始処理
        self.sleep_time = 5
        self.thread_flag = True
        self.management_thread()

        # restart実行されるのはスレッド上のため直接__file__使えない
        
        #print(self.file_name)
        #self.path = sys.executable
        #TODO パスの認識方法
        self.path = "/usr/bin/python3"

    def connect(self):
        self.port = 6379
        self.blackboard = redis.StrictRedis(host=self.host, port=self.port, db=0)

        self.pubsub = self.blackboard.pubsub()
        # マネジメントトピックも購読対象に追加
        self.pubsub.psubscribe(**{self.topic: self.on_message, "coterie-management": self.receive_management})
        self.pubsub_thread = self.pubsub.run_in_thread(sleep_time=0.01)

        self.on_connect()
        print("[LOG] Network Access - OK")

    def send_management(self, msg: AgentMessage, qos=2):
        # マネジメントトピックへのパブリッシュメソッド
        self.blackboard.publish("coterie-management", msg.to_json())

    def terminate(self):
        #トピックの購読スレッドとマネジメントスレッドの終了処理
        # TODO なんかCtrl+C効かない
        self.thread_flag = False
        #self.thread.join()
        msg = AgentMessage()
        msg.To = "management_agent"
        msg.From = self.name
        msg.Args = {"status":"Terminated"}
        self.send_management(msg, qos=0)
        self.pubsub_thread.stop()
        self.pubsub.close()
        print(self.name+" is Terminated.")
        sys.exit()

    def restart(self):
        #トピックの購読スレッドとマネジメントスレッドの終了処理
        # TODO なんかCtrl+C効かない
        msg = AgentMessage()
        msg.To = "management_agent"
        msg.From = self.name
        msg.Args = {"status":"Restarting"}
        self.send_management(msg, qos=0)
        self.pubsub_thread.stop()
        self.pubsub.close()
        print(self.name+" is Restarting.")
        os.execl(self.path, 'python', self.file_name)

    """
    for override
    """
    def management_thread(self):
        # マネジメントスレッド 指定時間でループ
        if not self.thread_flag: 
            sys.exit()
        msg = AgentMessage()
        msg.To = "management_agent"
        msg.From = self.name
        msg.Args = {"status":self.status}
        self.send_management(msg, qos=0)
        self.thread = threading.Timer(self.sleep_time,self.management_thread)
        self.thread.start()
        
    # callback when receive msg from "management" topic
    def receive_management(self, msg):
        data = msg['data'].decode()
        agt_msg = AgentMessage(data)

        if agt_msg.To in (self.name, "ALL") and agt_msg.From == "management_agent":
            self.status = agt_msg.Args["status"]
            if self.status == "Terminated":
                self.terminate()
            elif self.status == "Restarting":
                self.restart()

class CasWorkerAgent(CasBaseAgent):
    ACTIONS = {
        'worker_test' : 'worker_test'
    }
    def __init__(self, name, file_name, dir_path="/settings", auto_load=True, local=True, coterie="Experiment", host="127.0.0.1") -> None:
        CasBaseAgent.__init__(self, name, file_name, auto_load, local, coterie, host)
        event_handler = MyHandler()
        self.observer = Observer()
        self.observer.schedule(event_handler, os.getcwd()+dir_path, recursive=True)
        self.observer.start()

    def receive_message(self, msg: AgentMessage):
        if msg.Action in self.ACTIONS and self.status == "Alive":
            action_name = self.ACTIONS[msg.Action]
            try:
                method = getattr(self, action_name)
            except AttributeError:
                print("[ERROR]", action_name, "is nothing.")
            method(msg)

    def worker_test(self, msg:AgentMessage):
        print(msg.Args)

    def management_thread(self):
        # マネジメントスレッド 指定時間でループ
        if not self.thread_flag: 
            sys.exit()
        if not MyHandler.flag: 
            self.restart()
        msg = AgentMessage()
        msg.To = "management_agent"
        msg.From = self.name
        msg.Args = {"status":self.status}
        self.send_management(msg, qos=0)
        self.thread = threading.Timer(self.sleep_time,self.management_thread)
        self.thread.start()

    def terminate(self):
        #トピックの購読スレッドとマネジメントスレッドの終了処理
        # TODO なんかCtrl+C効かない
        self.thread_flag = False
        self.observer.stop()
        self.observer.join()
        #self.thread.join()
        msg = AgentMessage()
        msg.To = "management_agent"
        msg.From = self.name
        msg.Args = {"status":"Terminated"}
        self.send_management(msg, qos=0)
        self.pubsub_thread.stop()
        self.pubsub.close()
        print(self.name+" is Terminated.")
        sys.exit()

    def restart(self):
        #トピックの購読スレッドとマネジメントスレッドの終了処理
        # TODO なんかCtrl+C効かない
        self.observer.stop()
        self.observer.join()
        msg = AgentMessage()
        msg.To = "management_agent"
        msg.From = self.name
        msg.Args = {"status":"Restarting"}
        self.send_management(msg, qos=0)
        self.pubsub_thread.stop()
        self.pubsub.close()
        print(self.name+" is Restarting.")
        os.execl(self.path, 'python', self.file_name)

class CasManagementAgent(CasBaseAgent):

    def __init__(self, auto_load=True, local=True):
        print("+----------------------+")
        print("| Manegement Agent dev |")
        print("+----------------------+")
        self.agts_status = {}
        CasBaseAgent.__init__(self, "management_agent",__file__, auto_load, local)
        self.sleep_time = 0.2

    def on_message(self, msg):
        data = msg['data'].decode()
        agt_msg = AgentMessage(data)
        # 通常トピックのALLは受け取らない
        # まあ通常トピック使ってないけど念のため
        if agt_msg.To == self.name and agt_msg.From != self.name:
            self.receive_message(agt_msg)

    # callback when receive msg from "management" topic
    def receive_management(self, msg):
        data = msg['data'].decode()
        agt_msg = AgentMessage(data)

        # コンソールからなら指示出し，それ以外ならステータス更新
        if agt_msg.To in (self.name, "ALL") and agt_msg.From != self.name:
            if agt_msg.From == "console_agent":
                order_msg = AgentMessage()
                order_msg.To = agt_msg.Args["To"]
                order_msg.From = self.name
                order_msg.Args = {"status":agt_msg.Args["status"]}
                self.send_management(order_msg)
                return
            self.agts_status[agt_msg.From] = {"msg":agt_msg, "status":agt_msg.Args["status"], "date":agt_msg.Date}

    def management_thread(self):
        now = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
        color_paret = {
            "Terminated":"30",
            "Disconnected":"31",
            "Restarting":"32",
            "Sleep":"34",
            "Alive":"37"
        }
        symbol_paret = {
            "Terminated":"●",
            "Disconnected":"×",
            "Restarting":"○",
            "Sleep":"-",
            "Alive":"●"
        }
        # ステータス表示
        print("Agents status")
        for k,v in self.agts_status.items():
            if now-v["date"] > 10 and v["status"] != "Terminated":
                v["status"]="Disconnected"
            print("  \033[{}m{} {}".format(color_paret[v["status"]],symbol_paret[v["status"]],k))
            print("    Status : {}".format(v["status"]))
            print("    Last status update : {}sec ago\033[0m\n".format(now-v["date"]))
        print("\033[{}A\033[J".format(str(len(self.agts_status)*4+1)),end="")
        #print("\033[J",end="")
        self.thread = threading.Timer(self.sleep_time,self.management_thread)
        self.thread.start()

class CasConsoleAgent(CasBaseAgent):
    def __init__(self,file_name):
        print("+-------------------+")
        print("| Console Agent dev |")
        print("+-------------------+")
        CasBaseAgent.__init__(self,"console_agent",file_name)
        self.send_order()

    def send_order(self):
        while True:
            time.sleep(1)
            msg = AgentMessage()
            msg.To = "management_agent"
            msg.From = self.name
            msg.Args = {"To":input("to? >"),"status":input("status? >")}
            self.send_management(msg)

    def management_thread(self):
        pass

    def terminate(self):
        pass

if __name__ == "__main__":
    agt = CasManagementAgent()

    """
    TODO 
    ConsoleAgent作成-OK
    Terminated送られた時の動作-OK
    CasBaseAgent作成-OK
    __file__使えない問題
    """



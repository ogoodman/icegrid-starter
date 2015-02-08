module icecap {
    module ibase {
        exception NotMaster {
        };

        interface MasterOrSlave {
            bool masterState(out long priority);
        };

        interface EventSource {
            void follow(string chan, string sink);
            void unfollow(string chan, string sinkId);
            void send(string chan, string msg); // demo only
        };

        interface EventLog extends EventSource {
            long append(string msg);
        };

        interface Antenna {
            void serverOnline(string serverId);
        };
    };
};

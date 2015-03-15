#include "base.ice"

module icecap {
    module istorage {
        exception NoShard {
            string path;
            string shard;
        };

        exception FileNotFound {
        };

        sequence<string> Strings;

        interface DataManager extends ibase::MasterOrSlave {
            ["amd"] void register(string addr) throws ibase::NotMaster;
            ["amd"] void remove(string addr) throws ibase::NotMaster;
            ["amd"] string getMasters() throws ibase::NotMaster;
        };

        interface DataNode {
            void addPeer(string shard, string addr, bool sync);
            void removePeer(string shard, string addr);
            void addShard(string shard);
            void removeData(string shard);
            void reset();
            ["amd"] string getState(bool register);
            void update(string info);
        };

        interface File extends DataNode {
            ["amd"] Strings list(string shard) throws NoShard;
            ["amd"] string read(string path) throws FileNotFound, NoShard;
            ["amd"] void write(string path, string data) throws NoShard;
            ["amd"] void remove(string path) throws NoShard;
            // debugging
            string readRep(string path) throws FileNotFound;
            void writeRep(string path, string data);
            Strings listRep(string shard);
            void removeRep(string path);
        };
    };
};

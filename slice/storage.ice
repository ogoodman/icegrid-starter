#include "base.ice"

module icecap {
    module istorage {
        exception FileNotFound {
        };

        sequence<string> Strings;

        interface DataManager extends ibase::MasterOrSlave {
            ["amd"] void register(string addr) throws ibase::NotMaster;
            ["amd"] void remove(string addr) throws ibase::NotMaster;
            ["amd"] string getMasters() throws ibase::NotMaster;
        };

        interface File {
            ["amd"] Strings list() throws ibase::NotMaster;
            ["amd"] string read(string path) throws FileNotFound, ibase::NotMaster;
            ["amd"] void write(string path, string data) throws ibase::NotMaster;
            // debugging
            string readRep(string path) throws FileNotFound;
            void writeRep(string path, string data);
            Strings listRep();
            // replication
            void update(string info);
            void addPeer(string shard, string addr, bool sync);
            void removePeer(string shard, string addr);
            void removeData(string shard);
            string getState();
        };
    };
};

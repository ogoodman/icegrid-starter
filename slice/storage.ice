#include "base.ice"

module icecap {
    module istorage {
        exception FileNotFound {
        };

        sequence<string> Strings;

        interface DataManager extends ibase::MasterOrSlave {
            ["amd"] void register(string addr) throws ibase::NotMaster;
            ["amd"] void remove(string addr) throws ibase::NotMaster;
        };

        interface File extends ibase::MasterOrSlave {
            ["amd"] Strings list() throws ibase::NotMaster;
            ["amd"] string read(string path) throws FileNotFound, ibase::NotMaster;
            ["amd"] void write(string path, string data) throws ibase::NotMaster;
            // debugging
            string readRep(string path) throws FileNotFound;
            Strings listRep();
            // replication
            void update(string info);
            Strings peers();
            void addPeer(string addr, bool sync);
            void removePeer(string addr);
            void removeData();
        };
    };
};

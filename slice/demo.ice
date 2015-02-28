#include "base.ice"

module icecap {
    module idemo {

        interface Printer extends ibase::MasterOrSlave {
            void printString(string s);
            int addOne(int n);
            int getRand();
            string serverId();
            ["amd"] string masterNode() throws ibase::NotMaster;
            ["amd"] int fact(int n);
        };

        exception FileNotFound {
        };

        sequence<string> Strings;

        interface File extends ibase::MasterOrSlave {
            ["amd"] Strings list() throws ibase::NotMaster;
            ["amd"] string read(string path) throws FileNotFound, ibase::NotMaster;
            ["amd"] void write(string path, string data) throws ibase::NotMaster;
            void addPeer(string addr); // replication
            void update(string info); // replication
        };
    };
};

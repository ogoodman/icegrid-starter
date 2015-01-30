#include "base.ice"

module icecap {
    module idemo {

        interface Printer extends ibase::MasterOrSlave {
            void printString(string s);
            int addOne(int n);
            int getRand();
            string masterNode() throws ibase::NotMaster;
            string serverId();
            ["amd"] string callOther();
        };

        exception FileNotFound {
        };

        sequence<string> Strings;

        interface File {
            Strings list();
            string read(string path) throws FileNotFound;
            void write(string path, string data);
            void addReplica(string node, bool sync); // replication
            void update(string info); // replication
        };
    };
};

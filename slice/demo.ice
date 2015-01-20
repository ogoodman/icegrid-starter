#include "base.ice"

module icecap {
    module idemo {

        interface Printer extends ibase::MasterOrSlave {
            void printString(string s);
            int addOne(int n);
            int getRand();
            string masterNode() throws ibase::NotMaster;
            string serverId();
        };

        exception FileNotFound {
        };

        interface File {
            string read(string path) throws FileNotFound;
            void write(string path, string data);
            void update(string info); // replication
        };
    };
};

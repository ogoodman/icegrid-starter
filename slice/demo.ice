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

        interface File {
            Strings list();
            string read(string path) throws FileNotFound;
            void write(string path, string data);
            void update(string info); // replication
        };
    };
};

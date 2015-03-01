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
    };
};

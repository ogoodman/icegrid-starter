module icecap {
    module idemo {
        interface Printer {
            void printString(string s);
            int addOne(int n);
            int getRand();
            bool masterPriority(out long priority);
            string info();
        };
    };
};

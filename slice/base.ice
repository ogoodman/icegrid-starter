module icecap {
    module ibase {
        exception NotMaster {
        };

        interface MasterOrSlave {
            bool masterState(out long priority);
        };
    };
};

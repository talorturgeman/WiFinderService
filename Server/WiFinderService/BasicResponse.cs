﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace WiFinderService
{
    class BasicResponse
    {
        public bool Success { get; set; }
        public bool Encrypted { get; set; }
        public string Data { get; set; }
    }
}

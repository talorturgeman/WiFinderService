using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace WiFinderService
{
    public class PostDataResponse
    {
        public bool success;

        public PostDataResponse()
        {
                
        }

        public PostDataResponse(bool isSucceed)
        {
            this.success = isSucceed;
        }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace WiFinderService
{
    class TestClass
    {
        public static string ConvertTextToDecodedMessege(string text)
        {
            string str = Convert.ToBase64String(Encoding.UTF8.GetBytes(text));
            str.Replace('+', '-');
            str.Replace('/', '_');
            str.Replace('=', '.');
            return "enc_data=" + str;
        }
    }
}

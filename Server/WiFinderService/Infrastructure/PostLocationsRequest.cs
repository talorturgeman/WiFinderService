using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;

namespace WiFinderService.Infrastructure
{
    class PostLocationsRequest
    {
        public string ident_key { get; set; }
        public IEnumerable<Device> data { get; set; }

        public class Device
        {
            public string mac;
            public string bssid;
            public string power;
            public string timestamp; //todo - convert to long
        };

        public bool UpdateDB()
        {
            return true;
        }

        public static void Parse(string body)
        {
            /*
            string key = "24e61e0d591341aa9d86890f56a212bb";
            byte[] keyarr = Encoding.UTF8.GetBytes(key);
            byte[] result = EncryptStringToBytes(body, keyarr);
            string str = Convert.ToBase64String(result);
            */
            string key = "24e61e0d591341aa9d86890f56a212bb";
            string stage3 = body.Substring(9);
            Byte[] stage2 = Convert.FromBase64String(stage3);
            byte[] keyarr = Encoding.UTF8.GetBytes(key);
           // Array.Resize(ref keyarr, 32);
            byte[] iv = new byte[32];
            string stage1try = DecryptRJ256(stage2, key);
            string stage1 = DecryptStringFromBytes(stage2, keyarr, iv);
        }

        static string DecryptStringFromBytes(byte[] cipherText, byte[] key, byte[] iv)
        {
            if (cipherText == null || cipherText.Length <= 0)
                throw new ArgumentNullException("cipherText");
            if (key == null || key.Length <= 0)
                throw new ArgumentNullException("key");

            string plainText;
            var rijndael = new RijndaelManaged()
            {
                Key = key,
                Mode = CipherMode.ECB,
                BlockSize = 256,
            };
            ICryptoTransform decryptor = rijndael.CreateDecryptor(rijndael.Key, rijndael.IV);

            using (var memoryStream = new MemoryStream(cipherText))
            {
                using (var cryptoStream = new CryptoStream(memoryStream, decryptor, CryptoStreamMode.Read))
                {
                    using (var streamReader = new StreamReader(cryptoStream))
                    {
                        plainText = streamReader.ReadToEnd();
                    }
                }
            }
            return plainText;
        }

        static byte[] GetBytes(string str)
        {
            byte[] bytes = new byte[str.Length * sizeof(char)];
            bytes = Encoding.ASCII.GetBytes(str);
            Convert.ToBase64String(bytes);
            //System.Buffer.BlockCopy(str.ToCharArray(), 0, bytes, 0, bytes.Length);
            return bytes;
        }

        static public String DecryptRJ256(byte[] cypher, string KeyString)
        {
            var sRet = "";

            var encoding = new UTF8Encoding();
            var Key = encoding.GetBytes(KeyString);

            using (var rj = new RijndaelManaged())
            {
                try
                {
                    rj.Padding = PaddingMode.PKCS7;
                    rj.Mode = CipherMode.ECB;
                    rj.BlockSize = 256;
                    rj.Key = Key;
                    var ms = new MemoryStream(cypher);

                    using (var cs = new CryptoStream(ms, rj.CreateDecryptor(Key, rj.IV), CryptoStreamMode.Read))
                    {
                        using (var sr = new StreamReader(cs))
                        {
                            sRet = sr.ReadLine();
                        }
                    }
                }
                finally
                {
                    rj.Clear();
                }
            }

            return sRet;
        }
    }
}

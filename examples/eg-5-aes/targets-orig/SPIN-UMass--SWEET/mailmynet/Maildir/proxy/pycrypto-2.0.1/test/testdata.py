#
#  testdata.py : Test data for the various algorithms
#
# Part of the Python Cryptography Toolkit
#
# Distribute and use freely; there are no restrictions on further
# dissemination and usage except those imposed by the laws of your
# country of residence.  This software is provided "as is" without
# warranty of fitness for use or suitability for any purpose, express
# or implied. Use at your own risk or not at all.
#

#  Data for encryption algorithms is saved as (key, plaintext,
# ciphertext) tuples.  Hashing algorithm test data is simply
# (text, hashvalue) pairs.

# MD2 validation data

md2= [
     ("", "8350e5a3e24c153df2275c9f80692773"),
     ("a", "32ec01ec4a6dac72c0ab96fb34c0b5d1"),
     ("abc", "da853b0d3f88d99b30283a69e6ded6bb"),
     ("message digest", "ab4f496bfb2a530b219ff33031fe06b0"),
     ("abcdefghijklmnopqrstuvwxyz", "4e8ddff3650292ab5a4108c3aa47940b"),
     ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
      "da33def2a42df13975352846c30338cd"),
     ("12345678901234567890123456789012345678901234567890123456789012345678901234567890",
      "d5976f79d83d3a0dc9806c3c66f3efd8")
     ]

# MD4 validation data

md4= [
      ('', "31d6cfe0d16ae931b73c59d7e0c089c0"),
      ("a",   "bde52cb31de33e46245e05fbdbd6fb24"),
      ("abc",   "a448017aaf21d8525fc10ae87aa6729d"),
      ("message digest",   "d9130a8164549fe818874806e1c7014b"),
      ("abcdefghijklmnopqrstuvwxyz",   "d79e1c308aa5bbcdeea8ed63df412da9"),
      ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
       "043f8582f241db351ce627e153e7f0e4"),
      ("12345678901234567890123456789012345678901234567890123456789012345678901234567890",
      "e33b4ddc9c38f2199c3e7b164fcc0536"),
     ]

# MD5 validation data

md5= [
    ('',  "d41d8cd98f00b204e9800998ecf8427e"),
    ('a', "0cc175b9c0f1b6a831c399e269772661"),
    ('abc', "900150983cd24fb0d6963f7d28e17f72"),
    ('message digest', "f96b697d7cb7938d525a2f31aaf161d0"),
    ('abcdefghijklmnopqrstuvwxyz', "c3fcd3d76192e4007dfb496cca67e13b"),
    ('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
               "d174ab98d277d9f5a5611c2c9f419d9f"),
    ('12345678901234567890123456789012345678901234567890123456789'
     '012345678901234567890', "57edf4a22be3c955ac49da2e2107b67a")
     ]

# Test data for SHA, the Secure Hash Algorithm.

sha = [
       ('abc', "a9993e364706816aba3e25717850c26c9cd0d89d"),
       ('abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
        "84983e441c3bd26ebaae4aa1f95129e5e54670f1"),
       (1000000 * 'a', '34aa973cd4c4daa4f61eeb2bdbad27316534016f'),
      ]

sha256 = [
       ('abc', "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
       ("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
       ("abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu", 
        "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1"),
       ("Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal.  Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure. We are met on a great battlefield of that war.  We have come to dedicate a portion of that field, as a final resting place for those who here gave their lives that that nation might live.  It is altogether fitting and proper that we should do this.  But, in a larger sense, we can not dedicate--we can not consecrate--we can not hallow--this ground.  The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract.  The world will little note, nor long remember what we say here, but it can never forget what they did here.  It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here have thus far so nobly advanced.  It is rather for us to be here dedicated to the great task remaining before us--that from these honored dead we take increased devotion to that cause for which they gave the last full measure of devotion--that we here highly resolve that these dead shall not have died in vain--that this nation, under God, shall have a new birth of freedom--and that government of the people, by the people, for the people, shall not perish from the earth.  -- President Abraham Lincoln, November 19, 1863", 
        "4d25fccf8752ce470a58cd21d90939b7eb25f3fa418dd2da4c38288ea561e600"),
       ("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
       ("This is exactly 64 bytes long, not counting the terminating byte", "ab64eff7e88e2e46165e29f2bce41826bd4c7b3552f6b382a9e7d3af47c245f8"),
       ("For this sample, this 63-byte string will be used as input data", "f08a78cbbaee082b052ae0708f32fa1e50c5c421aa772ba5dbb406a2ea6be342"),
       ("And this textual data, astonishing as it may appear, is exactly 128 bytes in length, as are both SHA-384 and SHA-512 block sizes", 
        "0ab803344830f92089494fb635ad00d76164ad6e57012b237722df0d7ad26896"),
       ("By hashing data that is one byte less than a multiple of a hash block length (like this 127-byte string), bugs may be revealed.", 
        "e4326d0459653d7d3514674d713e74dc3df11ed4d30b4013fd327fdb9e394c26"),
       ("qwerty" * 65536,
        "5e3dfe0cc98fd1c2de2a9d2fd893446da43d290f2512200c515416313cdf3192"),
       ("Rijndael is AES" * 1024,
        "80fced5a97176a5009207cd119551b42c5b51ceb445230d02ecc2663bbfb483a"),
       (1000000 * 'a', 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0'),
       ]

ripemd = [ ("", "9c1185a5c5e9fc54612808977ee8f548b2258d31"),
           ("a", "0bdc9d2d256b3ee9daae347be6f4dc835a467ffe"),
           ("abc", "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"),
           ("message digest", "5d0689ef49d2fae572b881b123a85ffa21595f36"),
           ("abcdefghijklmnopqrstuvwxyz",
            "f71c27109c692c1b56bbdceb5b9d2865b3708dbc"),
           ("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "12a053384a9c0c88e405a06c27dcf49ada62eb2b"),
           ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
           "b0e20b6e3116640286ed3a87a5713079b21f5189"),
           (8 *"1234567890", "9b752e45573d4b39f4dbd3323cab82bf63326bfb"),
           (1000000 * 'a', "52783243c1697bdbe16d37f97f68f08325dc1528"),
]

#Test data for SHA256
sha256 = [("abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
          ("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", 
           "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
		   ("abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu", 
		   		"cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1"),
		   ("Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal.  Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure. We are met on a great battlefield of that war.  We have come to dedicate a portion of that field, as a final resting place for those who here gave their lives that that nation might live.  It is altogether fitting and proper that we should do this.  But, in a larger sense, we can not dedicate--we can not consecrate--we can not hallow--this ground.  The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract.  The world will little note, nor long remember what we say here, but it can never forget what they did here.  It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here have thus far so nobly advanced.  It is rather for us to be here dedicated to the great task remaining before us--that from these honored dead we take increased devotion to that cause for which they gave the last full measure of devotion--that we here highly resolve that these dead shall not have died in vain--that this nation, under God, shall have a new birth of freedom--and that government of the people, by the people, for the people, shall not perish from the earth.  -- President Abraham Lincoln, November 19, 1863", 
		   		"4d25fccf8752ce470a58cd21d90939b7eb25f3fa418dd2da4c38288ea561e600"),
		   ("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
		   ("This is exactly 64 bytes long, not counting the terminating byte", "ab64eff7e88e2e46165e29f2bce41826bd4c7b3552f6b382a9e7d3af47c245f8"),
		   ("For this sample, this 63-byte string will be used as input data", "f08a78cbbaee082b052ae0708f32fa1e50c5c421aa772ba5dbb406a2ea6be342"),
		   ("And this textual data, astonishing as it may appear, is exactly 128 bytes in length, as are both SHA-384 and SHA-512 block sizes", 
		   		"0ab803344830f92089494fb635ad00d76164ad6e57012b237722df0d7ad26896"),
		   ("By hashing data that is one byte less than a multiple of a hash block length (like this 127-byte string), bugs may be revealed.", 
		   		"e4326d0459653d7d3514674d713e74dc3df11ed4d30b4013fd327fdb9e394c26"),
		   ("qwerty" * 65536, 
    		    "5e3dfe0cc98fd1c2de2a9d2fd893446da43d290f2512200c515416313cdf3192"),
		   ("Rijndael is AES" * 1024, 
  	 	    "80fced5a97176a5009207cd119551b42c5b51ceb445230d02ecc2663bbfb483a"),
]
sha256 = sha256[:1]

# DES validation data

# Key, IV, plaintext, ciphertext
des_cbc= [('0123456789abcdef', 'fedcba9876543210',
           "7654321 Now is the time for \000\000\000\000", 'ccd173ffab2039f4acd8aefddfd8a1eb468e91157888ba681d269397f7fe62b4')]

des = [ ('0000000000000000', '0000000000000000', '8CA64DE9C1B123A7'),
    ('FFFFFFFFFFFFFFFF', 'FFFFFFFFFFFFFFFF', '7359B2163E4EDC58'),
    ('3000000000000000', '1000000000000001', '958E6E627A05557B'),
    ('1111111111111111', '1111111111111111', 'F40379AB9E0EC533'),
    ('0123456789ABCDEF', '1111111111111111', '17668DFC7292532D'),
    ('1111111111111111', '0123456789ABCDEF', '8A5AE1F81AB8F2DD'),
    ('0000000000000000', '0000000000000000', '8CA64DE9C1B123A7'),
    ('FEDCBA9876543210', '0123456789ABCDEF', 'ED39D950FA74BCC4'),
    ('7CA110454A1A6E57', '01A1D6D039776742', '690F5B0D9A26939B'),
    ('0131D9619DC1376E', '5CD54CA83DEF57DA', '7A389D10354BD271'),
    ('07A1133E4A0B2686', '0248D43806F67172', '868EBB51CAB4599A'),
    ('3849674C2602319E', '51454B582DDF440A', '7178876E01F19B2A'),
    ('04B915BA43FEB5B6', '42FD443059577FA2', 'AF37FB421F8C4095'),
    ('0113B970FD34F2CE', '059B5E0851CF143A', '86A560F10EC6D85B'),
    ('0170F175468FB5E6', '0756D8E0774761D2', '0CD3DA020021DC09'),
    ('43297FAD38E373FE', '762514B829BF486A', 'EA676B2CB7DB2B7A'),
    ('07A7137045DA2A16', '3BDD119049372802', 'DFD64A815CAF1A0F'),
    ('04689104C2FD3B2F', '26955F6835AF609A', '5C513C9C4886C088'),
    ('37D06BB516CB7546', '164D5E404F275232', '0A2AEEAE3FF4AB77'),
    ('1F08260D1AC2465E', '6B056E18759F5CCA', 'EF1BF03E5DFA575A'),
    ('584023641ABA6176', '004BD6EF09176062', '88BF0DB6D70DEE56'),
    ('025816164629B007', '480D39006EE762F2', 'A1F9915541020B56'),
    ('49793EBC79B3258F', '437540C8698F3CFA', '6FBF1CAFCFFD0556'),
    ('4FB05E1515AB73A7', '072D43A077075292', '2F22E49BAB7CA1AC'),
    ('49E95D6D4CA229BF', '02FE55778117F12A', '5A6B612CC26CCE4A'),
    ('018310DC409B26D6', '1D9D5C5018F728C2', '5F4C038ED12B2E41'),
    ('1C587F1C13924FEF', '305532286D6F295A', '63FAC0D034D9F793'),
    ('0101010101010101', '0123456789ABCDEF', '617B3A0CE8F07100'),
    ('1F1F1F1F0E0E0E0E', '0123456789ABCDEF', 'DB958605F8C8C606'),
    ('E0FEE0FEF1FEF1FE', '0123456789ABCDEF', 'EDBFD1C66C29CCC7'),
    ('0000000000000000', 'FFFFFFFFFFFFFFFF', '355550B2150E2451'),
    ('FFFFFFFFFFFFFFFF', '0000000000000000', 'CAAAAF4DEAF1DBAE'),
    ('0123456789ABCDEF', '0000000000000000', 'D5D44FF720683D0D'),
    ('FEDCBA9876543210', 'FFFFFFFFFFFFFFFF', '2A2BB008DF97C2F2'),
    ('0101010101010101', '95F8A5E5DD31D900', '8000000000000000'),
    ('0101010101010101', 'DD7F121CA5015619', '4000000000000000'),
    ('0101010101010101', '2E8653104F3834EA', '2000000000000000'),
    ('0101010101010101', '4BD388FF6CD81D4F', '1000000000000000'),
    ('0101010101010101', '20B9E767B2FB1456', '0800000000000000'),
    ('0101010101010101', '55579380D77138EF', '0400000000000000'),
    ('0101010101010101', '6CC5DEFAAF04512F', '0200000000000000'),
    ('0101010101010101', '0D9F279BA5D87260', '0100000000000000'),
    ('0101010101010101', 'D9031B0271BD5A0A', '0080000000000000'),
    ('0101010101010101', '424250B37C3DD951', '0040000000000000'),
    ('0101010101010101', 'B8061B7ECD9A21E5', '0020000000000000'),
    ('0101010101010101', 'F15D0F286B65BD28', '0010000000000000'),
    ('0101010101010101', 'ADD0CC8D6E5DEBA1', '0008000000000000'),
    ('0101010101010101', 'E6D5F82752AD63D1', '0004000000000000'),
    ('0101010101010101', 'ECBFE3BD3F591A5E', '0002000000000000'),
    ('0101010101010101', 'F356834379D165CD', '0001000000000000'),
    ('0101010101010101', '2B9F982F20037FA9', '0000800000000000'),
    ('0101010101010101', '889DE068A16F0BE6', '0000400000000000'),
    ('0101010101010101', 'E19E275D846A1298', '0000200000000000'),
    ('0101010101010101', '329A8ED523D71AEC', '0000100000000000'),
    ('0101010101010101', 'E7FCE22557D23C97', '0000080000000000'),
    ('0101010101010101', '12A9F5817FF2D65D', '0000040000000000'),
    ('0101010101010101', 'A484C3AD38DC9C19', '0000020000000000'),
    ('0101010101010101', 'FBE00A8A1EF8AD72', '0000010000000000'),
    ('0101010101010101', '750D079407521363', '0000008000000000'),
    ('0101010101010101', '64FEED9C724C2FAF', '0000004000000000'),
    ('0101010101010101', 'F02B263B328E2B60', '0000002000000000'),
    ('0101010101010101', '9D64555A9A10B852', '0000001000000000'),
    ('0101010101010101', 'D106FF0BED5255D7', '0000000800000000'),
    ('0101010101010101', 'E1652C6B138C64A5', '0000000400000000'),
    ('0101010101010101', 'E428581186EC8F46', '0000000200000000'),
    ('0101010101010101', 'AEB5F5EDE22D1A36', '0000000100000000'),
    ('0101010101010101', 'E943D7568AEC0C5C', '0000000080000000'),
    ('0101010101010101', 'DF98C8276F54B04B', '0000000040000000'),
    ('0101010101010101', 'B160E4680F6C696F', '0000000020000000'),
    ('0101010101010101', 'FA0752B07D9C4AB8', '0000000010000000'),
    ('0101010101010101', 'CA3A2B036DBC8502', '0000000008000000'),
    ('0101010101010101', '5E0905517BB59BCF', '0000000004000000'),
    ('0101010101010101', '814EEB3B91D90726', '0000000002000000'),
    ('0101010101010101', '4D49DB1532919C9F', '0000000001000000'),
    ('0101010101010101', '25EB5FC3F8CF0621', '0000000000800000'),
    ('0101010101010101', 'AB6A20C0620D1C6F', '0000000000400000'),
    ('0101010101010101', '79E90DBC98F92CCA', '0000000000200000'),
    ('0101010101010101', '866ECEDD8072BB0E', '0000000000100000'),
    ('0101010101010101', '8B54536F2F3E64A8', '0000000000080000'),
    ('0101010101010101', 'EA51D3975595B86B', '0000000000040000'),
    ('0101010101010101', 'CAFFC6AC4542DE31', '0000000000020000'),
    ('0101010101010101', '8DD45A2DDF90796C', '0000000000010000'),
    ('0101010101010101', '1029D55E880EC2D0', '0000000000008000'),
    ('0101010101010101', '5D86CB23639DBEA9', '0000000000004000'),
    ('0101010101010101', '1D1CA853AE7C0C5F', '0000000000002000'),
    ('0101010101010101', 'CE332329248F3228', '0000000000001000'),
    ('0101010101010101', '8405D1ABE24FB942', '0000000000000800'),
    ('0101010101010101', 'E643D78090CA4207', '0000000000000400'),
    ('0101010101010101', '48221B9937748A23', '0000000000000200'),
    ('0101010101010101', 'DD7C0BBD61FAFD54', '0000000000000100'),
    ('0101010101010101', '2FBC291A570DB5C4', '0000000000000080'),
    ('0101010101010101', 'E07C30D7E4E26E12', '0000000000000040'),
    ('0101010101010101', '0953E2258E8E90A1', '0000000000000020'),
    ('0101010101010101', '5B711BC4CEEBF2EE', '0000000000000010'),
    ('0101010101010101', 'CC083F1E6D9E85F6', '0000000000000008'),
    ('0101010101010101', 'D2FD8867D50D2DFE', '0000000000000004'),
    ('0101010101010101', '06E7EA22CE92708F', '0000000000000002'),
    ('0101010101010101', '166B40B44ABA4BD6', '0000000000000001'),
    ('8001010101010101', '0000000000000000', '95A8D72813DAA94D'),
    ('4001010101010101', '0000000000000000', '0EEC1487DD8C26D5'),
    ('2001010101010101', '0000000000000000', '7AD16FFB79C45926'),
    ('1001010101010101', '0000000000000000', 'D3746294CA6A6CF3'),
    ('0801010101010101', '0000000000000000', '809F5F873C1FD761'),
    ('0401010101010101', '0000000000000000', 'C02FAFFEC989D1FC'),
    ('0201010101010101', '0000000000000000', '4615AA1D33E72F10'),
    ('0180010101010101', '0000000000000000', '2055123350C00858'),
    ('0140010101010101', '0000000000000000', 'DF3B99D6577397C8'),
    ('0120010101010101', '0000000000000000', '31FE17369B5288C9'),
    ('0110010101010101', '0000000000000000', 'DFDD3CC64DAE1642'),
    ('0108010101010101', '0000000000000000', '178C83CE2B399D94'),
    ('0104010101010101', '0000000000000000', '50F636324A9B7F80'),
    ('0102010101010101', '0000000000000000', 'A8468EE3BC18F06D'),
    ('0101800101010101', '0000000000000000', 'A2DC9E92FD3CDE92'),
    ('0101400101010101', '0000000000000000', 'CAC09F797D031287'),
    ('0101200101010101', '0000000000000000', '90BA680B22AEB525'),
    ('0101100101010101', '0000000000000000', 'CE7A24F350E280B6'),
    ('0101080101010101', '0000000000000000', '882BFF0AA01A0B87'),
    ('0101040101010101', '0000000000000000', '25610288924511C2'),
    ('0101020101010101', '0000000000000000', 'C71516C29C75D170'),
    ('0101018001010101', '0000000000000000', '5199C29A52C9F059'),
    ('0101014001010101', '0000000000000000', 'C22F0A294A71F29F'),
    ('0101012001010101', '0000000000000000', 'EE371483714C02EA'),
    ('0101011001010101', '0000000000000000', 'A81FBD448F9E522F'),
    ('0101010801010101', '0000000000000000', '4F644C92E192DFED'),
    ('0101010401010101', '0000000000000000', '1AFA9A66A6DF92AE'),
    ('0101010201010101', '0000000000000000', 'B3C1CC715CB879D8'),
    ('0101010180010101', '0000000000000000', '19D032E64AB0BD8B'),
    ('0101010140010101', '0000000000000000', '3CFAA7A7DC8720DC'),
    ('0101010120010101', '0000000000000000', 'B7265F7F447AC6F3'),
    ('0101010110010101', '0000000000000000', '9DB73B3C0D163F54'),
    ('0101010108010101', '0000000000000000', '8181B65BABF4A975'),
    ('0101010104010101', '0000000000000000', '93C9B64042EAA240'),
    ('0101010102010101', '0000000000000000', '5570530829705592'),
    ('0101010101800101', '0000000000000000', '8638809E878787A0'),
    ('0101010101400101', '0000000000000000', '41B9A79AF79AC208'),
    ('0101010101200101', '0000000000000000', '7A9BE42F2009A892'),
    ('0101010101100101', '0000000000000000', '29038D56BA6D2745'),
    ('0101010101080101', '0000000000000000', '5495C6ABF1E5DF51'),
    ('0101010101040101', '0000000000000000', 'AE13DBD561488933'),
    ('0101010101020101', '0000000000000000', '024D1FFA8904E389'),
    ('0101010101018001', '0000000000000000', 'D1399712F99BF02E'),
    ('0101010101014001', '0000000000000000', '14C1D7C1CFFEC79E'),
    ('0101010101012001', '0000000000000000', '1DE5279DAE3BED6F'),
    ('0101010101011001', '0000000000000000', 'E941A33F85501303'),
    ('0101010101010801', '0000000000000000', 'DA99DBBC9A03F379'),
    ('0101010101010401', '0000000000000000', 'B7FC92F91D8E92E9'),
    ('0101010101010201', '0000000000000000', 'AE8E5CAA3CA04E85'),
    ('0101010101010180', '0000000000000000', '9CC62DF43B6EED74'),
    ('0101010101010140', '0000000000000000', 'D863DBB5C59A91A0'),
    ('0101010101010120', '0000000000000000', 'A1AB2190545B91D7'),
    ('0101010101010110', '0000000000000000', '0875041E64C570F7'),
    ('0101010101010108', '0000000000000000', '5A594528BEBEF1CC'),
    ('0101010101010104', '0000000000000000', 'FCDB3291DE21F0C0'),
    ('0101010101010102', '0000000000000000', '869EFD7F9F265A09'),
    ('1046913489980131', '0000000000000000', '88D55E54F54C97B4'),
    ('1007103489988020', '0000000000000000', '0C0CC00C83EA48FD'),
    ('10071034C8980120', '0000000000000000', '83BC8EF3A6570183'),
    ('1046103489988020', '0000000000000000', 'DF725DCAD94EA2E9'),
    ('1086911519190101', '0000000000000000', 'E652B53B550BE8B0'),
    ('1086911519580101', '0000000000000000', 'AF527120C485CBB0'),
    ('5107B01519580101', '0000000000000000', '0F04CE393DB926D5'),
    ('1007B01519190101', '0000000000000000', 'C9F00FFC74079067'),
    ('3107915498080101', '0000000000000000', '7CFD82A593252B4E'),
    ('3107919498080101', '0000000000000000', 'CB49A2F9E91363E3'),
    ('10079115B9080140', '0000000000000000', '00B588BE70D23F56'),
    ('3107911598080140', '0000000000000000', '406A9A6AB43399AE'),
    ('1007D01589980101', '0000000000000000', '6CB773611DCA9ADA'),
    ('9107911589980101', '0000000000000000', '67FD21C17DBB5D70'),
    ('9107D01589190101', '0000000000000000', '9592CB4110430787'),
    ('1007D01598980120', '0000000000000000', 'A6B7FF68A318DDD3'),
    ('1007940498190101', '0000000000000000', '4D102196C914CA16'),
    ('0107910491190401', '0000000000000000', '2DFA9F4573594965'),
    ('0107910491190101', '0000000000000000', 'B46604816C0E0774'),
    ('0107940491190401', '0000000000000000', '6E7E6221A4F34E87'),
    ('19079210981A0101', '0000000000000000', 'AA85E74643233199'),
    ('1007911998190801', '0000000000000000', '2E5A19DB4D1962D6'),
    ('10079119981A0801', '0000000000000000', '23A866A809D30894'),
    ('1007921098190101', '0000000000000000', 'D812D961F017D320'),
    ('100791159819010B', '0000000000000000', '055605816E58608F'),
    ('1004801598190101', '0000000000000000', 'ABD88E8B1B7716F1'),
    ('1004801598190102', '0000000000000000', '537AC95BE69DA1E1'),
    ('1004801598190108', '0000000000000000', 'AED0F6AE3C25CDD8'),
    ('1002911598100104', '0000000000000000', 'B3E35A5EE53E7B8D'),
    ('1002911598190104', '0000000000000000', '61C79C71921A2EF8'),
    ('1002911598100201', '0000000000000000', 'E2F5728F0995013C'),
    ('1002911698100101', '0000000000000000', '1AEAC39A61F0A464'),
    ('7CA110454A1A6E57', '01A1D6D039776742', '690F5B0D9A26939B'),
    ('0131D9619DC1376E', '5CD54CA83DEF57DA', '7A389D10354BD271'),
    ('07A1133E4A0B2686', '0248D43806F67172', '868EBB51CAB4599A'),
    ('3849674C2602319E', '51454B582DDF440A', '7178876E01F19B2A'),
    ('04B915BA43FEB5B6', '42FD443059577FA2', 'AF37FB421F8C4095'),
    ('0113B970FD34F2CE', '059B5E0851CF143A', '86A560F10EC6D85B'),
    ('0170F175468FB5E6', '0756D8E0774761D2', '0CD3DA020021DC09'),
    ('43297FAD38E373FE', '762514B829BF486A', 'EA676B2CB7DB2B7A'),
    ('07A7137045DA2A16', '3BDD119049372802', 'DFD64A815CAF1A0F'),
    ('04689104C2FD3B2F', '26955F6835AF609A', '5C513C9C4886C088'),
    ('37D06BB516CB7546', '164D5E404F275232', '0A2AEEAE3FF4AB77'),
    ('1F08260D1AC2465E', '6B056E18759F5CCA', 'EF1BF03E5DFA575A'),
    ('584023641ABA6176', '004BD6EF09176062', '88BF0DB6D70DEE56'),
    ('025816164629B007', '480D39006EE762F2', 'A1F9915541020B56'),
    ('49793EBC79B3258F', '437540C8698F3CFA', '6FBF1CAFCFFD0556'),
    ('4FB05E1515AB73A7', '072D43A077075292', '2F22E49BAB7CA1AC'),
    ('49E95D6D4CA229BF', '02FE55778117F12A', '5A6B612CC26CCE4A'),
    ('018310DC409B26D6', '1D9D5C5018F728C2', '5F4C038ED12B2E41'),
    ('1C587F1C13924FEF', '305532286D6F295A', '63FAC0D034D9F793') ]


# Test data for Alleged RC4

arc4 = [ ('0000000000000000', '0000000000000000', 'de188941a3375d3a'),
         ('0123456789abcdef', '0123456789abcdef', '75b7878099e0c596'),
         ('0123456789abcdef', '0000000000000000', '7494c2e7104b0879'),
         ('ef012345', '00000000000000000000', 'd6a141a7ec3c38dfbd61') ]

# Test data for IDEA

idea = [('00010002000300040005000600070008', '0000000100020003', '11fbed2b01986de5'),
        ('00010002000300040005000600070008', '0102030405060708', '540E5FEA18C2F8B1'),
        ('00010002000300040005000600070008', '0019324B647D96AF', '9F0A0AB6E10CED78'),
        ('00010002000300040005000600070008', 'F5202D5B9C671B08', 'CF18FD7355E2C5C5'),
        ('00010002000300040005000600070008', 'FAE6D2BEAA96826E', '85DF52005608193D'),
        ('00010002000300040005000600070008', '0A141E28323C4650', '2F7DE750212FB734'),
        ('00010002000300040005000600070008', '050A0F14191E2328', '7B7314925DE59C09'),
        ('0005000A000F00140019001E00230028', '0102030405060708', '3EC04780BEFF6E20'),
        ('3A984E2000195DB32EE501C8C47CEA60', '0102030405060708', '97BCD8200780DA86'),
        ('006400C8012C019001F4025802BC0320', '05320A6414C819FA', '65BE87E7A2538AED'),
        ('9D4075C103BC322AFB03E7BE6AB30006', '0808080808080808', 'F5DB1AC45E5EF9F9')
       ];

# Test data for RC5

rc5 = [('10200c1000000000000000000000000000000000', '0000000000000000',
        '21A5DBEE154B8F6D'),
       ('10200c10915F4619BE41B2516355A50110A9CE91', '21A5DBEE154B8F6D',
        'F7C013AC5B2B8952'),
       ('10200c10783348E75AEB0F2FD7B169BB8DC16787', 'F7C013AC5B2B8952',
        '2F42B3B70369FC92'),
       ('10200c10DC49DB1375A5584F6485B413B5F12BAF', '2F42B3B70369FC92',
        '65C178B284D197CC'),
       ('10200c105269F149D41BA0152497574D7F153125', '65C178B284D197CC',
        'EB44E415DA319824')
      ]

# Test data for ARC2
arc2 = [
('5068696c6970476c617373', '0000000000000000', '624fb3e887419e48'),
('5068696c6970476c617373', 'ffffffffffffffff', '79cadef44c4a5a85'),
('5068696c6970476c617373', '0001020304050607', '90411525b34e4c2c'),
('5068696c6970476c617373', '0011223344556677', '078656aaba61cbfb'),
('ffffffffffffffff', '0000000000000000', 'd7bcc5dbb4d6e56a'),
('ffffffffffffffff', 'ffffffffffffffff', '7259018ec557b357'),
('ffffffffffffffff', '0001020304050607', '93d20a497f2ccb62'),
('ffffffffffffffff', '0011223344556677', 'cb15a7f819c0014d'),
('ffffffffffffffff5065746572477265656e6177617953e5ffe553', '0000000000000000', '63ac98cdf3843a7a'),
('ffffffffffffffff5065746572477265656e6177617953e5ffe553', 'ffffffffffffffff', '3fb49e2fa12371dd'),
('ffffffffffffffff5065746572477265656e6177617953e5ffe553', '0001020304050607', '46414781ab387d5f'),
('ffffffffffffffff5065746572477265656e6177617953e5ffe553', '0011223344556677', 'be09dc81feaca271'),
('53e5ffe553', '0000000000000000', 'e64221e608be30ab'),
('53e5ffe553', 'ffffffffffffffff', '862bc60fdcd4d9a9'),
('53e5ffe553', '0001020304050607', '6a34da50fa5e47de'),
('53e5ffe553', '0011223344556677', '584644c34503122c'),
]

# Test data for Blowfish

blowfish = [('6162636465666768696a6b6c6d6e6f707172737475767778797a',
             '424c4f5746495348', '324ed0fef413a203'),
            ('57686f206973204a6f686e2047616c743f', 'fedcba9876543210',
             'cc91732b8022f684')
           ]

# Test data for DES3

des3_cbc=[]

des3= [('0123456789abcdeffedcba9876543210', '0123456789abcde7',
        '7f1d0a77826b8aff'),
      ]

# The DES test data can also be used to construct DES3 test data.
for key, iv, plain, cipher in des_cbc:
    des3_cbc.append((key*3, iv, plain, cipher))
for key, plain, cipher in des:
    des3.append((key*3, plain, cipher))

# Test data for CAST

_castkey = '0123456712345678234567893456789A'
_castdata = '0123456789ABCDEF'

cast = [(_castkey,      _castdata, '238B4FE5847E44B2'),
        (_castkey[:10*2], _castdata, 'EB6A711A2C02271B'),
        (_castkey[: 5*2], _castdata, '7AC816D16E9B302E'),
        ]

# Test data for XOR

xor = []

# Test data for AES

aes = [# 128-bit key
       ('000102030405060708090A0B0C0D0E0F',
        '00112233445566778899AABBCCDDEEFF',
        '69C4E0D86A7B0430D8CDB78070B4C55A'),

       # 192-bit key
       ('000102030405060708090A0B0C0D0E0F1011121314151617',
        '00112233445566778899AABBCCDDEEFF',
        'DDA97CA4864CDFE06EAF70A0EC0D7191'),

       # 256-bit key
       ('000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F',
        '00112233445566778899AABBCCDDEEFF',
        '8EA2B7CA516745BFEAFC49904B496089'),
      ]

# Test data for AES modes, from NIST SP800-38A
from Crypto.Cipher import AES

counter_blocks = ['\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff',
                  '\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xff\x00',
                  '\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xff\x01',
                  '\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xff\x02'
                  ]


class ctr:
    def __init__ (self):
        self.index = 0

    def __call__ (self):
        block = counter_blocks[self.index]
        self.index = (self.index+1) % len(counter_blocks)
        return block

aes_modes = [
    (AES.MODE_CBC,
     '2b7e151628aed2a6abf7158809cf4f3c',
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('7649abac8119b246cee98e9b12e9197d'
      '5086cb9b507219ee95db113a917678b2'
      '73bed6b8e3c1743b7116e69e22229516'
      '3ff1caa1681fac09120eca307586e1a7'
      ),
     {'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'} ),
    (AES.MODE_CBC,
     '8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b',
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('4f021db243bc633d7178183a9fa071e8'
      'b4d9ada9ad7dedf4e5e738763f69145a'
      '571b242012fb7ae07fa9baac3df102e0'
      '08b0e27988598881d920a9e64f5615cd'
      ),
     {'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'} ),
    (AES.MODE_CBC,
     ('603deb1015ca71be2b73aef0857d7781'
      '1f352c073b6108d72d9810a30914dff4'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('f58c4c04d6e5f1ba779eabfb5f7bfbd6'
      '9cfc4e967edb808d679f777bc6702c7d'
      '39f23369a9d9bacfa530e26304231461'
      'b2eb05e2c39be9fcda6c19078c6a9d1b'
      ),
     {'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'} ),

    (AES.MODE_OFB,
     ('2b7e151628aed2a6abf7158809cf4f3c'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('3b3fd92eb72dad20333449f8e83cfb4a'
      '7789508d16918f03f53c52dac54ed825'
      '9740051e9c5fecf64344f7a82260edcc'
      '304c6528f659c77866a510d9c1d6ae5e'
      ),
     {'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'} ),
    (AES.MODE_OFB,
     ('8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('cdc80d6fddf18cab34c25909c99a4174'
      'fcc28b8d4c63837c09e81700c1100401'
      '8d9a9aeac0f6596f559c6d4daf59a5f2'
      '6d9f200857ca6c3e9cac524bd9acc92a'
      ),
     {'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'} ),
    (AES.MODE_OFB,
     ('603deb1015ca71be2b73aef0857d7781'
      '1f352c073b6108d72d9810a30914dff4'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('dc7e84bfda79164b7ecd8486985d3860'
      '4febdc6740d20b3ac88f6ad82a4fb08d'
      '71ab47a086e86eedf39d1c5bba97c408'
      '0126141d67f37be8538f5a8be740e484'
      ),
     {'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'} ),

    (AES.MODE_CTR,
     ('2b7e151628aed2a6abf7158809cf4f3c'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('874d6191b620e3261bef6864990db6ce'
      '9806f66b7970fdff8617187bb9fffdff'
      '5ae4df3edbd5d35e5b4f09020db03eab'
      '1e031dda2fbe03d1792170a0f3009cee'
      ),
     {'counter':ctr()} ),
    (AES.MODE_CTR,
     ('8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('1abc932417521ca24f2b0459fe7e6e0b'
      '090339ec0aa6faefd5ccc2c6f4ce8e94'
      '1e36b26bd1ebc670d1bd1d665620abf7'
      '4f78a7f6d29809585a97daec58c6b050'
      ),
     {'counter':ctr()} ),
    (AES.MODE_CTR,
     ('603deb1015ca71be2b73aef0857d7781'
      '1f352c073b6108d72d9810a30914dff4'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     ('601ec313775789a5b7a7f504bbf3d228'
      'f443e3ca4d62b59aca84e990cacaf5c5'
      '2b0930daa23de94ce87017ba2d84988d'
      'dfc9c58db67aada613c2dd08457941a6'
      ),
     {'counter':ctr()} ),

    (AES.MODE_CFB,
     '2b7e151628aed2a6abf7158809cf4f3c',
     '6bc1bee22e409f96e93d7e117393172aae2d',
     '3b79424c9c0dd436bace9e0ed4586a4f32b9',
     {'segment_size':8,
      'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',
     }
    ),
    (AES.MODE_CFB,
     '8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b',
     '6bc1bee22e409f96e93d7e117393172aae2d',
     'cda2521ef0a905ca44cd057cbf0d47a0678a',
     {'segment_size':8,
      'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',
     }
    ),
    (AES.MODE_CFB,
     ('603deb1015ca71be2b73aef0857d7781'
      '1f352c073b6108d72d9810a30914dff4'
      ),
     '6bc1bee22e409f96e93d7e117393172aae2d',
     'dc1f1a8520a64db55fcc8ac554844e889700',
     {'segment_size':8,
      'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',
     }
    ),

    (AES.MODE_CFB,
     ('2b7e151628aed2a6abf7158809cf4f3c'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     (
      '3b3fd92eb72dad20333449f8e83cfb4a'
      'c8a64537a0b3a93fcde3cdad9f1ce58b'
      '26751f67a3cbb140b1808cf187a4f4df'
      'c04b05357c5d1c0eeac4c66f9ff7f2e6'
     ),
     {'segment_size':128,
      'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',
     }
    ),
    (AES.MODE_CFB,
     ('8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     (
      'cdc80d6fddf18cab34c25909c99a4174'
      '67ce7f7f81173621961a2b70171d3d7a'
      '2e1e8a1dd59b88b1c8e60fed1efac4c9'
      'c05f9f9ca9834fa042ae8fba584b09ff'
     ),
     {'segment_size':128,
      'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',
     }
    ),
    (AES.MODE_CFB,
     ('603deb1015ca71be2b73aef0857d7781'
      '1f352c073b6108d72d9810a30914dff4'
      ),
     ('6bc1bee22e409f96e93d7e117393172a'
      'ae2d8a571e03ac9c9eb76fac45af8e51'
      '30c81c46a35ce411e5fbc1191a0a52ef'
      'f69f2445df4f9b17ad2b417be66c3710'
      ),
     (
      'dc7e84bfda79164b7ecd8486985d3860'
      '39ffed143b28b1c832113c6331e5407b'
      'df10132415e54b92a13ed0a8267ae2f9'
      '75a385741ab9cef82031623d55b1e471'
     ),
     {'segment_size':128,
      'IV':'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f',
     }
    ),
    ]

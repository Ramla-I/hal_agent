from defs import UserContext, Manufacturer

DEVICE_NAME = "rm0091"

user_contexts = [
    UserContext(device_name='82579', peripheral_name='', manufacturer=Manufacturer.INTEL, driver_path='devices/82579/e1000_ebb2314.rs', datasheet_path='devices/82579/82579.md', datasheet_sections_directory='', svd_path=[], run=0, file_id='file-Y42TiuVyte2z2TcbsXt9sv', vs_id='vs_68924fa6726481918501140c8ac86afe'),
    UserContext(device_name='82599', peripheral_name='', manufacturer=Manufacturer.INTEL, driver_path='devices/82599/ixgbe_4a124f4.rs', datasheet_path='devices/82599/82599.md', datasheet_sections_directory='', svd_path=[], run=0, file_id='file-RdWHHvaJvfkRZ59zXGjVVS', vs_id='vs_68924fdcb9cc8191809cacd7be13a9ea'),
    UserContext(device_name='rm0041', peripheral_name='STK', manufacturer=Manufacturer.STM, driver_path='', datasheet_path='devices/rm0041/rm0041.md', datasheet_sections_directory='devices/rm0041/sections', svd_path=['devices/rm0041/stm32f100.svd'], run='1', file_id='file-MHtC1XNEQDa2X8jNEjfk1b', vs_id='vs_6892501067b08191ac63cc6de06ee629'),
    UserContext(device_name='rm0090', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', datasheet_path='devices/rm0090/rm0090.md', datasheet_sections_directory='devices/rm0090/sections', svd_path=[
        'devices/rm0090/stm32f405.svd',
        'devices/rm0090/stm32f407.svd',
        'devices/rm0090/stm32f415.svd',
        'devices/rm0090/stm32f417.svd',
        'devices/rm0090/stm32f427.svd',
        'devices/rm0090/stm32f429.svd',
        'devices/rm0090/stm32f437.svd',
        'devices/rm0090/stm32f439.svd',
    ], run=1, file_id='file-CjEojSnvTNU3hpXQFG6DK5', vs_id='vs_689f5188906c81919cebc07c132a8f46'),
    UserContext(device_name='rm0091', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', datasheet_path='devices/rm0091/rm0091.md', datasheet_sections_directory='devices/rm0091/sections', svd_path=['devices/rm0091/stm32f0x2.svd', 'devices/rm0091/stm32f0x1.svd', 'devices/rm0091/stm32f0x8.svd'], run=1, file_id='file-T2XMpz886q7hQNqaDhN7Fn', vs_id='vs_689f52468484819182c9c3085572ce19'),
    UserContext(device_name='rm0360', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', datasheet_path='devices/rm0360/rm0360.md', datasheet_sections_directory='devices/rm0360/sections', svd_path=['devices/rm0360/stm32f0x0.svd'], run=0, file_id='file-JT7wee34qTEUtugwxW2VAP', vs_id='vs_689f52862f5881918366547ab0417608'),
    UserContext(device_name='rm0364', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', datasheet_path='devices/rm0364/rm0364.md', datasheet_sections_directory='devices/rm0364/sections', svd_path=['devices/rm0364/stm32f3x4.svd'], run=0, file_id='file-WyPzwzxKUmAS2iv41KeADs', vs_id='vs_689f52c5e2a881918c5e0925915ca939'),
    UserContext(device_name='rm0490', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', datasheet_path='devices/rm0490/rm0490.md', datasheet_sections_directory='devices/rm0490/sections', svd_path=['devices/rm0490/stm32c031.svd', 'devices/rm0490/stm32c011.svd', 'devices/rm0490/stm32c071.svd'], run=0, file_id='file-RygxVqtujcgLnFBQGrQ1in', vs_id='vs_689f52efc4bc8191afb9b4fb05c78f6c'),
]

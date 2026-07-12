# kế hoạch code và liên kết nội dung

## cách hợp nhất hai phần công việc

Không chia dự án theo người thực hiện. Mọi chức năng đi qua một lớp điều phối chung là `RecordService`. Nhờ vậy, phần mật mã và phần quản lý dữ liệu luôn được gọi trong cùng một luồng và cùng một giao dịch SQLite.

```text
routes.py
   ↓
record_service.py
   ├── student.py
   ├── aes_cipher.py
   ├── hashing.py
   ├── repository.py
   ├── block.py
   └── verify.py
```

`routes.py` không được tự mã hóa, tự viết câu lệnh SQLite hoặc tự tính băm. Tệp này chỉ nhận dữ liệu biểu mẫu, gọi dịch vụ và hiển thị kết quả.

## cụ thể từng phần code gì

| phần | tệp chính | nội dung cần chịu trách nhiệm |
|---|---|---|
| cấu hình | `src/config.py` | đọc `.env`, kiểm tra khóa AES đủ 32 byte, xác định đường dẫn SQLite |
| mô hình hồ sơ | `src/domain/student.py` | chuẩn hóa mã sinh viên, họ tên, ngày sinh, chương trình, học phần và điểm |
| tuần tự hóa | `src/encryption/serialization.py` | chuyển dữ liệu sang JSON chuẩn hóa và tạo dữ liệu xác thực bổ sung |
| mã hóa | `src/encryption/aes_cipher.py` | AES-GCM, nonce 12 byte, giải mã và phát hiện sai thẻ xác thực |
| chỉ mục kín | `src/integrity/hashing.py` | dẫn xuất khóa chỉ mục, HMAC mã sinh viên, SHA-256 phong bì mã hóa |
| kết nối dữ liệu | `src/database/connection.py` | mở SQLite, bật khóa ngoại và điều khiển giao dịch |
| lược đồ | `src/database/schema.py` | tạo `records`, `record_versions`, `audit_blocks` và các ràng buộc |
| truy cập dữ liệu | `src/database/repository.py` | câu lệnh thêm, đọc và cập nhật, không chứa quyết định nghiệp vụ |
| cấu trúc khối | `src/blockchain/block.py` | dữ liệu một khối và cách tính `block_hash` |
| chuỗi khối | `src/blockchain/chain.py` | khối đầu tiên, nối khối, kiểm tra chiều cao và liên kết |
| xác minh | `src/verification/verify.py` | kiểm tra chuỗi, SHA-256 phong bì và xác thực AES-GCM |
| điều phối | `src/services/record_service.py` | thêm, sửa, xóa, đọc, tìm kiếm và xác minh trong một luồng thống nhất |
| ứng dụng Flask | `src/web/app.py` | tạo ứng dụng, khởi tạo dịch vụ, cấu hình phiên và xử lý lỗi |
| địa chỉ giao diện | `src/web/routes.py` | nhận biểu mẫu, gọi dịch vụ, chuyển kết quả sang trang HTML |
| trang hiển thị | `src/web/templates/` | bảng điều khiển, hồ sơ, khối và xác minh |
| kiểu trình bày | `src/web/static/` | giao diện và thao tác thêm hàng học phần |
| dữ liệu mô phỏng | `experiments/generate_dataset.py` | sinh tập 100, 1.000 và 10.000 hồ sơ có thể tái lập |
| đo thực nghiệm | `experiments/run_experiment.py` | đo ba cấu hình và giữ kết quả thô |
| biểu đồ | `experiments/make_figures.py` | tạo hình từ kết quả thống kê, không nhập số liệu bằng tay |
| kiểm thử | `tests/` | chứng minh từng lớp và toàn bộ luồng hoạt động đúng |

## luồng thêm hồ sơ

1. `routes.py` nhận các trường từ biểu mẫu.
2. `student.py` chuẩn hóa và từ chối dữ liệu sai.
3. Dịch vụ tạo UUID nội bộ và HMAC từ mã sinh viên.
4. `aes_cipher.py` mã hóa JSON hồ sơ bằng AES-GCM.
5. `hashing.py` băm đầy đủ mã nội bộ, phiên bản, thao tác, nonce và bản mã.
6. `repository.py` ghi phiên bản mã hóa.
7. `chain.py` nối một khối `CREATE` vào đầu chuỗi hiện tại.
8. Cả bản ghi và khối được xác nhận trong cùng một giao dịch.

Nếu bước 6 hoặc 7 thất bại, toàn bộ thao tác phải được hoàn tác.

## luồng cập nhật hồ sơ

1. Đọc và giải mã phiên bản hiện tại.
2. So sánh `expected_version` để ngăn ghi đè thay đổi mới hơn.
3. Chuẩn hóa nội dung mới và kiểm tra mã sinh viên không trùng.
4. Tạo nonce mới và phiên bản tăng thêm một.
5. Ghi phong bì mã hóa mới, giữ nguyên phiên bản cũ.
6. Nối khối `UPDATE` và cập nhật con trỏ phiên bản hiện tại.

## luồng xóa hồ sơ

1. Đọc snapshot hiện tại.
2. Mã hóa lại snapshot bằng nonce mới với thao tác `DELETE`.
3. Tạo phiên bản tiếp theo và khối `DELETE`.
4. Chuyển trạng thái bản ghi thành `deleted`.

Không xóa vật lý phiên bản cũ vì lịch sử sẽ không còn kiểm chứng được.

## luồng xác minh

Xác minh toàn hệ thống gồm ba lớp:

1. Tính lại `block_hash` và kiểm tra `previous_hash` của từng khối.
2. Tính lại SHA-256 của từng phong bì mã hóa và so sánh với khối tương ứng.
3. Giải mã AES-GCM để kiểm tra thẻ xác thực và dữ liệu JSON.

Kết quả phải nêu lỗi cụ thể thay vì chỉ trả về đúng hoặc sai.

## kế hoạch sáu tuần gắn với mã nguồn

### tuần 1, từ 19/06 đến 26/06

* tạo cấu trúc dự án, môi trường ảo, `.gitignore`, tệp thư viện và ứng dụng Flask tối thiểu
* viết mục mở đầu và tập hợp nguồn tham khảo
* đầu ra là kho mã chạy được và câu hỏi nghiên cứu rõ ràng

### tuần 2, từ 27/06 đến 04/07

* code `domain`, `database/schema.py`, `database/repository.py` và cấu trúc `Block`
* vẽ kiến trúc, luồng dữ liệu và lược đồ SQLite
* viết phần hệ thống đề xuất và bản nháp mô hình mật mã

### tuần 3, từ 05/07 đến 12/07

* code AES-GCM, JSON chuẩn hóa, HMAC, SHA-256, nối khối và xác minh
* viết kiểm thử Unicode, nonce, thẻ xác thực và liên kết khối
* hoàn thiện mô hình mật mã và môi trường cài đặt

### tuần 4, từ 13/07 đến 20/07

* code `RecordService` và đặt toàn bộ thao tác trong giao dịch nguyên tử
* nối giao diện quản lý hồ sơ, trang khối và trang xác minh
* chạy kiểm thử tích hợp và chụp ảnh giao diện
* hoàn thiện phần cài đặt trong báo cáo

### tuần 5, từ 21/07 đến 28/07

* sinh dữ liệu 100, 1.000 và 10.000 hồ sơ
* chạy ba cấu hình với 30 lần lặp
* thử thay đổi trái phép và tạo biểu đồ
* viết thiết lập thực nghiệm, kết quả và thảo luận từ số liệu thật

### tuần 6, từ 29/07 đến 04/08

* hoàn thiện giới hạn, hướng phát triển, kết luận và tóm tắt
* đưa nội dung vào mẫu FAIR 2026
* rà soát trích dẫn, hình, bảng, công thức và kiểm thử lại trên môi trường sạch

## thứ tự nên mở tệp trong Visual Studio Code

1. Đọc `src/domain/student.py` để hiểu dữ liệu hợp lệ.
2. Đọc `src/encryption/aes_cipher.py` và `src/integrity/hashing.py` để hiểu lớp bảo vệ.
3. Đọc `src/database/schema.py` để hiểu dữ liệu thực tế được lưu.
4. Đọc `src/blockchain/block.py` để hiểu cách một khối được băm.
5. Đọc `src/services/record_service.py` để thấy mọi phần được nối với nhau.
6. Đọc `src/web/routes.py` để thấy giao diện gọi nghiệp vụ.
7. Đọc `tests/` để biết mỗi yêu cầu được chứng minh ra sao.
8. Đọc `experiments/run_experiment.py` trước khi thu số liệu báo cáo.

## tiêu chí hoàn thành trước khi đo

* mã hóa và giải mã đúng tiếng Việt
* hai lần mã hóa cùng dữ liệu có nonce khác nhau
* sai nonce, bản mã, thẻ hoặc dữ liệu xác thực bổ sung đều thất bại
* SQLite không chứa mã sinh viên hoặc họ tên dạng rõ
* thêm hồ sơ tạo phiên bản 1 và khối `CREATE`
* cập nhật tạo phiên bản mới và khối `UPDATE`
* xóa logic tạo khối `DELETE`
* sửa hoặc xóa một khối làm xác minh thất bại
* khởi động lại ứng dụng không làm mất chuỗi
* toàn bộ kiểm thử tự động thành công


import xlwings as xw
import numpy as np
import os
import time
import sys
def calculate_excel_formulas(file_path, visible=False):# 打开excel计算公式函数
    app = None
    wb = None
    try:
        app = xw.App(visible=visible, add_book=False)# 启动Excel应用
        print(f"open the file: {file_path}")
        for attempt in range(3):  # 尝试打开工作簿，如果失败则重试
            try:
                wb = app.books.open(file_path)
                break
            except Exception as e:
                print(f"Failed to open the file. Try {attempt + 1}/3: {str(e)}")
                time.sleep(2)  # 等待2秒后重试
                if attempt == 2:
                    raise RuntimeError(f"Failed to open the Excel file: {file_path}")
        print("being calculated...")        # 计算整个工作簿
        try:   # 使用多种方法确保公式被计算
            wb.api.Calculate()  # 方法1
        except:
            try:
                app.api.CalculateFull()  # 方法2
            except:
                try:
                    app.api.Calculation = xw.constants.Calculation.xlCalculationManual # 方法3：手动触发计算
                    app.api.Calculation = xw.constants.Calculation.xlCalculationAutomatic
                except Exception as e:
                    print(f"Error during calculation: {str(e)}")
        time.sleep(3)  # 增加等待时间确保计算完成
        print("being saved...")
        wb.save()     # 保存文件
        wb.close()    # 关闭工作簿
        print(f"has been completed and saved successfully: {file_path}")
        return True
    except Exception as e:
        print(f"An error occurred during the processing: {str(e)}")
        return False
    finally:   # 确保Excel应用退出
        try:
            if app is not None:
                app.quit()
        except:
            pass
        if sys.platform.startswith('win'):    # 强制终止可能残留的Excel进程（仅Windows）
            os.system('taskkill /f /im excel.exe >nul 2>&1')
            time.sleep(1)  # 给系统时间结束进程
def main():
    try:
        print("Before empolying this method, correct your baseline and peak position")
        text_address = input("Please enter your text path:")
        data = np.loadtxt(text_address, delimiter=',') # 若分隔符为逗号将delimiter=','；若为空格，改为delimiter=None
        x_original, y_original = data[:, 0], data[:, 1]
        x_new = np.arange(2599.92775, 3500.37163, 0.394931521929825)
        y_new = np.interp(x_new, x_original, y_original)
        np.savetxt("Text reconstructed by interpolation method.txt", np.column_stack((x_new, y_new)), delimiter=",") # 保存插值结果
        text_data = np.loadtxt("Text reconstructed by interpolation method.txt", delimiter=",")
        y_text = text_data[:, 1] # 提取y值列
        excel_path = None
        while True:# 写入Excel
            answer = input("Containing amide peak？(y/n)：").strip().lower()
            if answer == 'y':
                excel_path = "MPs containing amide peak.xlsx"
                break
            elif answer == 'n':
                excel_path = "MPs without amide peak.xlsx"
                break
            else:
                print("Please input y or n")
        app = xw.App(visible=False, add_book=False)    # 使用xlwings写入数据
        wb = app.books.open(excel_path)
        sht = wb.sheets['Search']
        start_cell = sht.range('B2') # 批量写入数据（提高性能）
        end_cell = sht.range(f'B{2282}')
        data_range = sht.range(start_cell, end_cell)
        data_range.value = y_text.reshape(-1, 1)  # 确保是列向量
        wb.save()   # 保存并关闭
        wb.close()
        app.quit()
        print("Data writing has been completed")
        if not calculate_excel_formulas(excel_path, visible=False): # 计算Excel公式
            print("The formula calculation failed. Try to read the result using other methods")
        app = xw.App(visible=False, add_book=False)  # 读取计算结果
        wb = app.books.open(excel_path)
        sht = wb.sheets['Search']
        c2_result = sht.range('C2').value  # 直接读取计算结果
        d2_result = sht.range('D2').value
        if c2_result < 0.6:
            print("Non-MP")
        elif c2_result >= 0.6 and c2_result < 0.75:
            print("Unclassified MP")
        else:
            print(f"Matching degree：{c2_result:.4f}")
            print(f"MP polymer type：{d2_result}")
        wb.close()  # 保存并退出
        app.quit()
    except Exception as e:
        print(f"The main program has an error: {str(e)}")
    finally:
        # 确保所有Excel进程关闭
        if sys.platform.startswith('win'):
            os.system('taskkill /f /im excel.exe >nul 2>&1')
if __name__ == "__main__":
    main()
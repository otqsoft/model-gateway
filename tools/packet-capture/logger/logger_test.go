package logger

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestDailyRotateWriter_WriteCreatesFile(t *testing.T) {
	dir := t.TempDir()
	w, err := NewDailyRotateWriter(dir, "test")
	if err != nil {
		t.Fatalf("NewDailyRotateWriter: %v", err)
	}
	defer w.Close()

	msg := "hello daily log\n"
	n, err := w.Write([]byte(msg))
	if err != nil {
		t.Fatalf("Write: %v", err)
	}
	if n != len(msg) {
		t.Errorf("Write returned %d, want %d", n, len(msg))
	}

	// 文件名应包含今天的日期
	today := time.Now().Format("2006-01-02")
	expected := filepath.Join(dir, "test-"+today+".log")
	if w.CurrentFile() != expected {
		t.Errorf("CurrentFile() = %q, want %q", w.CurrentFile(), expected)
	}

	// 读回文件内容
	data, err := os.ReadFile(expected)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if !strings.Contains(string(data), "hello daily log") {
		t.Errorf("file content %q does not contain expected message", string(data))
	}
}

func TestDailyRotateWriter_RotateOnDateChange(t *testing.T) {
	dir := t.TempDir()
	w, err := NewDailyRotateWriter(dir, "rot")
	if err != nil {
		t.Fatalf("NewDailyRotateWriter: %v", err)
	}
	defer w.Close()

	// 模拟昨天的日期
	yesterday := time.Now().AddDate(0, 0, -1).Format("2006-01-02")
	w.mu.Lock()
	w.curDate = yesterday // 手动篡改内部日期，触发轮转
	w.mu.Unlock()

	_, err = w.Write([]byte("new day\n"))
	if err != nil {
		t.Fatalf("Write after simulated date change: %v", err)
	}

	today := time.Now().Format("2006-01-02")
	expectedNew := filepath.Join(dir, "rot-"+today+".log")
	if w.CurrentFile() != expectedNew {
		t.Errorf("after rotate CurrentFile() = %q, want %q", w.CurrentFile(), expectedNew)
	}
}

func TestNewTeeWriter(t *testing.T) {
	var buf1, buf2 strings.Builder
	tee := NewTeeWriter(&buf1, &buf2)
	msg := "tee test\n"
	tee.Write([]byte(msg))
	if buf1.String() != msg {
		t.Errorf("buf1 = %q, want %q", buf1.String(), msg)
	}
	if buf2.String() != msg {
		t.Errorf("buf2 = %q, want %q", buf2.String(), msg)
	}
}

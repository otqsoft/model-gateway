// Package logger 提供每日自动轮转的日志写入器。
// 不依赖任何第三方日志轮转库，通过在每次 Write 时检查日期决定是否切换文件。
package logger

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// DailyRotateWriter 每天自动创建新日志文件的写入器。
// 文件命名格式：<dir>/<prefix>-YYYY-MM-DD.log
// 实现了 io.Writer 接口，可直接传给 logrus.SetOutput。
type DailyRotateWriter struct {
	dir      string // 日志目录
	prefix   string // 文件名前缀，如 "app"
	mu       sync.Mutex
	file     *os.File
	curDate  string // 当前文件对应的日期 "2006-01-02"
}

// NewDailyRotateWriter 创建一个日志轮转写入器。
// dir 为日志目录，prefix 为文件名前缀（不含日期和扩展名）。
func NewDailyRotateWriter(dir, prefix string) (*DailyRotateWriter, error) {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create log dir %s: %w", dir, err)
	}
	w := &DailyRotateWriter{dir: dir, prefix: prefix}
	if err := w.rotate(); err != nil {
		return nil, err
	}
	return w, nil
}

// Write 实现 io.Writer。每次写入前检查日期，必要时轮转文件。
func (w *DailyRotateWriter) Write(p []byte) (n int, err error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	today := time.Now().Format("2006-01-02")
	if today != w.curDate {
		if err := w.rotate(); err != nil {
			// 轮转失败时继续写入旧文件，不中断日志
			_ = err
		}
	}
	if w.file == nil {
		return len(p), nil
	}
	return w.file.Write(p)
}

// CurrentFile 返回当前日志文件的路径（用于启动时日志输出提示）。
func (w *DailyRotateWriter) CurrentFile() string {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.file == nil {
		return ""
	}
	return w.file.Name()
}

// Close 关闭当前日志文件。
func (w *DailyRotateWriter) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.file != nil {
		err := w.file.Close()
		w.file = nil
		return err
	}
	return nil
}

// rotate 内部函数：打开今天的日志文件（不加锁，调用方负责加锁）。
func (w *DailyRotateWriter) rotate() error {
	today := time.Now().Format("2006-01-02")
	name := filepath.Join(w.dir, fmt.Sprintf("%s-%s.log", w.prefix, today))

	f, err := os.OpenFile(name, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return fmt.Errorf("open log file %s: %w", name, err)
	}

	// 关闭旧文件
	if w.file != nil {
		_ = w.file.Close()
	}
	w.file = f
	w.curDate = today
	return nil
}

// NewTeeWriter 返回一个同时写向多个 io.Writer 的组合写入器（类似 tee）。
// 常用于同时写文件和 stdout。
func NewTeeWriter(writers ...io.Writer) io.Writer {
	return io.MultiWriter(writers...)
}

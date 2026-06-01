package tray

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"os/exec"
	"runtime"
	"syscall"
	"unsafe"

	"github.com/getlantern/systray"
)

type Tray struct {
	port int
}

func NewTray(port int) *Tray {
	return &Tray{port: port}
}

func (t *Tray) Run(onExit func()) {
	systray.Run(t.onReady, onExit)
}

func (t *Tray) onReady() {
	iconData := generateIcon()
	systray.SetIcon(iconData)
	systray.SetTitle("")
	systray.SetTooltip("AI Token Monitor")

	mOpen := systray.AddMenuItem("打开主页", "在浏览器中打开监控面板")
	systray.AddSeparator()
	mQuit := systray.AddMenuItem("退出", "退出系统")

	go func() {
		for {
			select {
			case <-mOpen.ClickedCh:
				openBrowser(fmt.Sprintf("http://localhost:%d/", t.port))
			case <-mQuit.ClickedCh:
				if confirmExit() {
					systray.Quit()
					return
				}
			}
		}
	}()
}

func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}

func generateIcon() []byte {
	const size = 16
	img := image.NewRGBA(image.Rect(0, 0, size, size))

	bgColor := color.RGBA{0x1A, 0x73, 0xE8, 0xFF}
	for y := 0; y < size; y++ {
		for x := 0; x < size; x++ {
			img.Set(x, y, bgColor)
		}
	}

	letterColor := color.RGBA{0xFF, 0xFF, 0xFF, 0xFF}
	drawLetterT(img, letterColor, size)

	var pngBuf bytes.Buffer
	png.Encode(&pngBuf, img)

	return wrapPNGasICO(pngBuf.Bytes(), size)
}

func drawLetterT(img *image.RGBA, c color.RGBA, size int) {
	mid := size / 2
	for x := 2; x < size-2; x++ {
		img.Set(x, 2, c)
		img.Set(x, 3, c)
	}
	for y := 2; y < size-2; y++ {
		img.Set(mid, y, c)
		img.Set(mid+1, y, c)
	}
}

func wrapPNGasICO(pngData []byte, size int) []byte {
	var buf bytes.Buffer

	binary.Write(&buf, binary.LittleEndian, uint16(0))
	binary.Write(&buf, binary.LittleEndian, uint16(1))
	binary.Write(&buf, binary.LittleEndian, uint16(1))

	binary.Write(&buf, binary.LittleEndian, uint8(size))
	binary.Write(&buf, binary.LittleEndian, uint8(size))
	binary.Write(&buf, binary.LittleEndian, uint8(0))
	binary.Write(&buf, binary.LittleEndian, uint8(0))
	binary.Write(&buf, binary.LittleEndian, uint16(1))
	binary.Write(&buf, binary.LittleEndian, uint16(32))
	binary.Write(&buf, binary.LittleEndian, uint32(len(pngData)))
	binary.Write(&buf, binary.LittleEndian, uint32(22))

	buf.Write(pngData)

	return buf.Bytes()
}

var (
	user32         = syscall.NewLazyDLL("user32.dll")
	messageBoxProc = user32.NewProc("MessageBoxW")
)

const (
	mbYesNo      = 0x00000004
	mbIconQuestion = 0x00000020
	idYes        = 6
)

func confirmExit() bool {
	title, _ := syscall.UTF16PtrFromString("AI Token Monitor")
	text, _ := syscall.UTF16PtrFromString("确定要退出系统吗？")

	ret, _, _ := messageBoxProc.Call(
		0,
		uintptr(unsafe.Pointer(text)),
		uintptr(unsafe.Pointer(title)),
		mbYesNo|mbIconQuestion,
	)

	return ret == idYes
}

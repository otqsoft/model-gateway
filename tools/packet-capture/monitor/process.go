package monitor

import (
	"net"
	"strings"
	"sync"
	"time"

	psnet "github.com/shirou/gopsutil/v3/net"
	"github.com/shirou/gopsutil/v3/process"
	"github.com/sirupsen/logrus"
)

type IOSample struct {
	ReadBytes  uint64
	WriteBytes uint64
	SampleTime time.Time
}

type ProcessMonitor struct {
	mu          sync.RWMutex
	lastSamples map[string]map[int32]*IOSample
}

func NewProcessMonitor() *ProcessMonitor {
	return &ProcessMonitor{
		lastSamples: make(map[string]map[int32]*IOSample),
	}
}

func (pm *ProcessMonitor) FindProcessesByName(names []string) []int32 {
	var matchedPIDs []int32

	allPids, err := process.Pids()
	if err != nil {
		logrus.Errorf("Failed to get process list: %v", err)
		return nil
	}

	matched := make(map[int32]bool)

	for _, pid := range allPids {
		p, err := process.NewProcess(pid)
		if err != nil {
			continue
		}

		processName, err := p.Name()
		if err != nil {
			continue
		}

		nameLower := strings.ToLower(processName)
		for _, searchName := range names {
			if strings.Contains(nameLower, strings.ToLower(searchName)) {
				if !matched[pid] {
					matchedPIDs = append(matchedPIDs, pid)
					matched[pid] = true
				}
				break
			}
		}
	}

	return matchedPIDs
}

func (pm *ProcessMonitor) HasAnyActiveExternalConnection(pids []int32) bool {
	conns, err := psnet.Connections("tcp")
	if err != nil {
		logrus.Debugf("Failed to get connections: %v", err)
		return false
	}

	pidSet := make(map[int32]bool)
	for _, pid := range pids {
		pidSet[pid] = true
	}

	for _, conn := range conns {
		if !pidSet[conn.Pid] {
			continue
		}
		if conn.Status == "ESTABLISHED" {
			remoteAddr := conn.Raddr.IP
			if isExternalIP(remoteAddr) {
				return true
			}
		}
	}
	return false
}

func isExternalIP(ipStr string) bool {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return false
	}
	if ip.IsLoopback() {
		return false
	}
	if ip.IsLinkLocalUnicast() {
		return false
	}
	if ip.IsLinkLocalMulticast() {
		return false
	}
	if ip.IsUnspecified() {
		return false
	}
	return true
}

func (pm *ProcessMonitor) GetProcessIO(pid int32) (readBytes, writeBytes uint64, err error) {
	p, err := process.NewProcess(pid)
	if err != nil {
		return 0, 0, err
	}

	ioCounters, err := p.IOCounters()
	if err != nil {
		return 0, 0, err
	}

	return ioCounters.ReadBytes, ioCounters.WriteBytes, nil
}

type DeltaResult struct {
	SentDelta      uint64
	ReceivedDelta  uint64
	Running        bool
	HasNetworkConn bool
	PIDs           []int32
}

func (pm *ProcessMonitor) SampleAndCalculateDelta(appName string, processNames []string) *DeltaResult {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	pids := pm.FindProcessesByName(processNames)
	result := &DeltaResult{
		Running: len(pids) > 0,
		PIDs:    pids,
	}

	if !result.Running {
		delete(pm.lastSamples, appName)
		return result
	}

	result.HasNetworkConn = pm.HasAnyActiveExternalConnection(pids)

	if !result.HasNetworkConn {
		now := time.Now()
		currentSamples := make(map[int32]*IOSample)
		for _, pid := range pids {
			readBytes, writeBytes, err := pm.GetProcessIO(pid)
			if err != nil {
				continue
			}
			currentSamples[pid] = &IOSample{
				ReadBytes:  readBytes,
				WriteBytes: writeBytes,
				SampleTime: now,
			}
		}
		pm.lastSamples[appName] = currentSamples
		return result
	}

	now := time.Now()
	currentSamples := make(map[int32]*IOSample)
	currentPIDSet := make(map[int32]bool)

	for _, pid := range pids {
		currentPIDSet[pid] = true

		readBytes, writeBytes, err := pm.GetProcessIO(pid)
		if err != nil {
			continue
		}

		currentSamples[pid] = &IOSample{
			ReadBytes:  readBytes,
			WriteBytes: writeBytes,
			SampleTime: now,
		}

		if pm.lastSamples[appName] != nil {
			if lastSample, ok := pm.lastSamples[appName][pid]; ok {
				if readBytes >= lastSample.ReadBytes {
					result.ReceivedDelta += readBytes - lastSample.ReadBytes
				}
				if writeBytes >= lastSample.WriteBytes {
					result.SentDelta += writeBytes - lastSample.WriteBytes
				}
			}
		}
	}

	pm.lastSamples[appName] = currentSamples

	return result
}

func (pm *ProcessMonitor) GetRunningProcessNames(appName string, processNames []string) []string {
	pids := pm.FindProcessesByName(processNames)
	var names []string

	for _, pid := range pids {
		p, err := process.NewProcess(pid)
		if err != nil {
			continue
		}
		name, err := p.Name()
		if err != nil {
			continue
		}
		names = append(names, name)
	}

	return names
}

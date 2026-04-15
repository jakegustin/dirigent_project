/*
 * MIT License
 *
 * Copyright (c) 2024 EASL
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package placement_policy

import (
	"cluster_manager/internal/control_plane/core"
	"cluster_manager/pkg/synchronization"
	"math/rand"
	"strings"
)

const (
	nodeClassFast = "fast"
	nodeClassSlow = "slow"
)

type HierarchicalPolicy struct {
	fastHostnames map[string]struct{}
	slowHostnames map[string]struct{}
}

func NewHierarchicalPolicy(fastHostnames, slowHostnames []string) *HierarchicalPolicy {
	fastSet := make(map[string]struct{})
	for _, host := range fastHostnames {
		h := strings.TrimSpace(host)
		if h != "" {
			fastSet[h] = struct{}{}
		}
	}

	slowSet := make(map[string]struct{})
	for _, host := range slowHostnames {
		h := strings.TrimSpace(host)
		if h != "" {
			slowSet[h] = struct{}{}
		}
	}

	return &HierarchicalPolicy{
		fastHostnames: fastSet,
		slowHostnames: slowSet,
	}
}

func (p *HierarchicalPolicy) classifyNode(nodeName string) string {
	hostname := nodeName
	if idx := strings.LastIndex(nodeName, "-"); idx > 0 {
		hostname = nodeName[:idx]
	}

	if _, ok := p.fastHostnames[hostname]; ok {
		return nodeClassFast
	}

	if _, ok := p.slowHostnames[hostname]; ok {
		return nodeClassSlow
	}

	return ""
}

func calculateProjectedUtilization(node core.WorkerNodeInterface, requested *ResourceMap) float64 {
	if node.GetCpuCores() == 0 {
		return 100
	}

	currentUsedCores := (float64(node.GetCpuUsage()) / 100.0) * float64(node.GetCpuCores())
	projectedUsedCores := currentUsedCores + float64(requested.GetCPUCores())

	projectedUtilization := (projectedUsedCores / float64(node.GetCpuCores())) * 100.0
	if projectedUtilization > 100 {
		return 100
	}

	return projectedUtilization
}

func scoreNodeByClass(nodeClass string, utilization float64) int {
	underThreshold := utilization < 90

	switch nodeClass {
	case nodeClassFast:
		if underThreshold {
			return 100
		}
		return 25
	case nodeClassSlow:
		if underThreshold {
			return 50
		}
		return 10
	default:
		return 0
	}
}

func (p *HierarchicalPolicy) Place(storage synchronization.SyncStructure[string, core.WorkerNodeInterface], requested *ResourceMap) core.WorkerNodeInterface {
	schedulable := getSchedulableNodes(storage.GetValues())
	if len(schedulable) == 0 {
		return nil
	}

	var (
		selected      core.WorkerNodeInterface
		maxScore      = -1
		cntOfMaxScore uint64 = 1
	)

	for _, node := range schedulable {
		utilization := calculateProjectedUtilization(node, requested)
		nodeClass := p.classifyNode(node.GetName())
		score := scoreNodeByClass(nodeClass, utilization)

		if score > maxScore {
			maxScore = score
			selected = node
			cntOfMaxScore = 1
		} else if score == maxScore {
			cntOfMaxScore++
			if rand.Intn(int(cntOfMaxScore)) == 0 {
				selected = node
			}
		}
	}

	return selected
}

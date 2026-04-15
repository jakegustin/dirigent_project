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
	"sort"
	"strings"
	"sync/atomic"
)

type WeightedRoundRobinPolicy struct {
	fastHostnames map[string]struct{}
	slowHostnames map[string]struct{}
	counter       int64
}

func NewWeightedRoundRobinPolicy(fastHostnames, slowHostnames []string) *WeightedRoundRobinPolicy {
	fastSet := make(map[string]struct{})
	for _, h := range fastHostnames {
		h = strings.TrimSpace(h)
		if h != "" {
			fastSet[h] = struct{}{}
		}
	}

	slowSet := make(map[string]struct{})
	for _, h := range slowHostnames {
		h = strings.TrimSpace(h)
		if h != "" {
			slowSet[h] = struct{}{}
		}
	}

	return &WeightedRoundRobinPolicy{
		fastHostnames: fastSet,
		slowHostnames: slowSet,
	}
}

func (p *WeightedRoundRobinPolicy) classifyNode(nodeName string) string {
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

func (p *WeightedRoundRobinPolicy) Place(storage synchronization.SyncStructure[string, core.WorkerNodeInterface], _ *ResourceMap) core.WorkerNodeInterface {
	schedulable := getSchedulableNodes(storage.GetValues())
	if len(schedulable) == 0 {
		return nil
	}

	// Separate into fast and slow, sort by name for stable ordering
	var fast, slow []core.WorkerNodeInterface
	for _, node := range schedulable {
		if p.classifyNode(node.GetName()) == nodeClassFast {
			fast = append(fast, node)
		} else {
			slow = append(slow, node)
		}
	}

	sort.Slice(fast, func(i, j int) bool { return fast[i].GetName() < fast[j].GetName() })
	sort.Slice(slow, func(i, j int) bool { return slow[i].GetName() < slow[j].GetName() })

	// Fast nodes get 2 slots each, slow nodes get 1 — reflecting 2:1 clock speed ratio
	weighted := make([]core.WorkerNodeInterface, 0, 2*len(fast)+len(slow))
	for _, f := range fast {
		weighted = append(weighted, f, f)
	}
	weighted = append(weighted, slow...)

	idx := atomic.AddInt64(&p.counter, 1) % int64(len(weighted))
	return weighted[idx]
}

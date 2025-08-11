from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple
from collections import defaultdict
import sys
import time
import random


# 가능한 주사위 규칙들을 나타내는 enum
class DiceRule(Enum):
    ONE = 0
    TWO = 1
    THREE = 2
    FOUR = 3
    FIVE = 4
    SIX = 5
    CHOICE = 6
    FOUR_OF_A_KIND = 7
    FULL_HOUSE = 8
    SMALL_STRAIGHT = 9
    LARGE_STRAIGHT = 10
    YACHT = 11


# 입찰 방법을 나타내는 데이터클래스
@dataclass
class Bid:
    group: str  # 입찰 그룹 ('A' 또는 'B')
    amount: int  # 입찰 금액


# 주사위 배치 방법을 나타내는 데이터클래스
@dataclass
class DicePut:
    rule: DiceRule  # 배치 규칙
    dice: List[int]  # 배치할 주사위 목록


# 팀의 현재 상태를 관리하는 클래스
class GameState:
    def __init__(self):
        self.dice = []  # 현재 보유한 주사위 목록
        self.rule_score: List[Optional[int]] = [
            None
        ] * 12  # 각 규칙별 획득 점수 (사용하지 않았다면 None)
        self.bid_score = 0  # 입찰로 얻거나 잃은 총 점수

    def get_total_score(self) -> int:
        """현재까지 획득한 총 점수 계산 (상단/하단 점수 + 보너스 + 입찰 점수)"""
        basic = bonus = combination = 0

        # 기본 점수 규칙 계산 (ONE ~ SIX)
        basic = sum(score for score in self.rule_score[0:6] if score is not None)
        bonus = 35000 if basic >= 63000 else 0
        combination = sum(score for score in self.rule_score[6:12] if score is not None)

        return basic + bonus + combination + self.bid_score

    def bid(self, is_successful: bool, amount: int):
        """입찰 결과에 따른 점수 반영"""
        if is_successful:
            self.bid_score -= amount  # 성공시 베팅 금액만큼 점수 차감
        else:
            self.bid_score += amount  # 실패시 베팅 금액만큼 점수 획득

    def add_dice(self, new_dice: List[int]):
        """새로운 주사위들을 보유 목록에 추가"""
        self.dice.extend(new_dice)

    def use_dice(self, put: DicePut):
        """주사위를 사용하여 특정 규칙에 배치"""
        # 이미 사용한 규칙인지 확인
        assert (
            put.rule is not None and self.rule_score[put.rule.value] is None
        ), "Rule already used"

        # 주사위 제거 전에 로그 출력
        print(f"# Debug: Removing dice {put.dice} from {self.dice}", file=sys.stderr)
        
        for d in put.dice:
            # 주사위 목록에 있는 주사위 제거
            if d in self.dice:
                self.dice.remove(d)
            else:
                print(f"# Debug: Dice {d} not found in {self.dice}", file=sys.stderr)
                # 주사위가 없으면 에러 대신 무시
                continue

        # 해당 규칙의 점수 계산 및 저장
        assert put.rule is not None
        self.rule_score[put.rule.value] = self.calculate_score(put)

    @staticmethod
    def calculate_score(put: DicePut) -> int:
        """규칙에 따른 점수를 계산하는 함수"""
        rule, dice = put.rule, put.dice

        # 기본 규칙 점수 계산 (해당 숫자에 적힌 수의 합 × 1000점)
        if rule == DiceRule.ONE:
            return sum(d for d in dice if d == 1) * 1000
        if rule == DiceRule.TWO:
            return sum(d for d in dice if d == 2) * 1000
        if rule == DiceRule.THREE:
            return sum(d for d in dice if d == 3) * 1000
        if rule == DiceRule.FOUR:
            return sum(d for d in dice if d == 4) * 1000
        if rule == DiceRule.FIVE:
            return sum(d for d in dice if d == 5) * 1000
        if rule == DiceRule.SIX:
            return sum(d for d in dice if d == 6) * 1000
        if rule == DiceRule.CHOICE:  # 주사위에 적힌 모든 수의 합 × 1000점
            return sum(dice) * 1000
        if (
            rule == DiceRule.FOUR_OF_A_KIND
        ):  # 같은 수가 적힌 주사위가 4개 있다면, 주사위에 적힌 모든 수의 합 × 1000점, 아니면 0
            ok = any(dice.count(i) >= 4 for i in range(1, 7))
            return sum(dice) * 1000 if ok else 0
        if (
            rule == DiceRule.FULL_HOUSE
        ):  # 3개의 주사위에 적힌 수가 서로 같고, 다른 2개의 주사위에 적힌 수도 서로 같으면 주사위에 적힌 모든 수의 합 × 1000점, 아닐 경우 0점
            pair = triple = False
            for i in range(1, 7):
                cnt = dice.count(i)
                # 5개 모두 같은 숫자일 때도 인정
                if cnt == 2 or cnt == 5:
                    pair = True
                if cnt == 3 or cnt == 5:
                    triple = True
            return sum(dice) * 1000 if pair and triple else 0
        if (
            rule == DiceRule.SMALL_STRAIGHT
        ):  # 4개의 주사위에 적힌 수가 1234, 2345, 3456중 하나로 연속되어 있을 때, 15000점, 아닐 경우 0점
            e1, e2, e3, e4, e5, e6 = [dice.count(i) > 0 for i in range(1, 7)]
            ok = (
                (e1 and e2 and e3 and e4)
                or (e2 and e3 and e4 and e5)
                or (e3 and e4 and e5 and e6)
            )
            return 15000 if ok else 0
        if (
            rule == DiceRule.LARGE_STRAIGHT
        ):  # 5개의 주사위에 적힌 수가 12345, 23456중 하나로 연속되어 있을 때, 30000점, 아닐 경우 0점
            e1, e2, e3, e4, e5, e6 = [dice.count(i) > 0 for i in range(1, 7)]
            ok = (e1 and e2 and e3 and e4 and e5) or (e2 and e3 and e4 and e5 and e6)
            return 30000 if ok else 0
        if (
            rule == DiceRule.YACHT
        ):  # 5개의 주사위에 적힌 수가 모두 같을 때 50000점, 아닐 경우 0점
            ok = any(dice.count(i) == 5 for i in range(1, 7))
            return 50000 if ok else 0

        assert False, "Invalid rule"


# 게임 상태를 관리하는 클래스
class Game:
    def __init__(self):
        self.my_state = GameState()  # 내 팀의 현재 상태
        self.opp_state = GameState()  # 상대 팀의 현재 상태
        self.current_round = 0  # 현재 턴 번호
        self.opponent_bids = {}  # 상대방의 각 턴별 입찰 가격 저장
        self.start_time = time.time()  # 게임 시작 시간
        self.opponent_yacht_completed = False  # 상대방이 YACHT를 완성했는지 여부
        self.my_yacht_completed = False  # 내가 YACHT를 완성했는지 여부

    def log_time(self, message: str):
        """시간 로그를 출력하는 함수"""
        elapsed = time.time() - self.start_time
        print(f"# Debug: [{elapsed:.3f}s] {message}", file=sys.stderr)

    def get_max_duplicate_count(self, dice_group: List[int]) -> int:
        """주사위 그룹에서 가장 많이 중복된 숫자의 개수를 반환하는 함수 (사용 가능한 규칙만 고려)"""
        counts = [0] * 7  # 1~6까지의 개수 (인덱스 0은 사용하지 않음)
        
        # 각 숫자의 개수 세기
        for dice in dice_group:
            counts[dice] += 1
        
        # SMALL_STRAIGHT, LARGE_STRAIGHT, YACHT가 모두 달성되었는지 확인
        small_straight_completed = self.my_state.rule_score[DiceRule.SMALL_STRAIGHT.value] is not None
        large_straight_completed = self.my_state.rule_score[DiceRule.LARGE_STRAIGHT.value] is not None
        yacht_completed = self.my_state.rule_score[DiceRule.YACHT.value] is not None
        high_rules_completed = small_straight_completed and large_straight_completed and yacht_completed
        
        # 사용 가능한 기본 규칙들만 고려 (이미 달성한 규칙은 제외)
        max_count = 0
        
        if high_rules_completed:
            # 고점수 규칙들이 달성된 경우: 큰 수부터 우선순위 (6 > 5 > 4 > 3 > 2 > 1)
            for num in range(6, 0, -1):  # 6부터 1까지 역순
                rule_index = num - 1  # 6→5(SIX), 5→4(FIVE), ..., 1→0(ONE)
                # 해당 규칙이 아직 사용되지 않았고, 고점수 규칙들이 모두 달성된 상태에서만 고려
                if self.my_state.rule_score[rule_index] is None:
                    if counts[num] > max_count:
                        max_count = counts[num]
                        # 가장 큰 수에서 최대 중복을 찾으면 바로 반환 (더 큰 우선순위)
                        break
        else:
            # 기존 로직: 단순히 가장 많이 중복된 개수만 반환 (사용 가능한 규칙만)
            for num in range(1, 7):
                rule_index = num - 1  # 1→0(ONE), 2→1(TWO), ..., 6→5(SIX)
                # 해당 규칙이 아직 사용되지 않았으면 고려
                if self.my_state.rule_score[rule_index] is None:
                    max_count = max(max_count, counts[num])
        
        return max_count

    def save_opponent_bid(self, round_num: int, bid_amount: int):
        """상대방의 입찰 가격을 저장하는 함수"""
        self.opponent_bids[round_num] = bid_amount

    def check_opponent_yacht_completion(self):
        """상대방이 YACHT를 완성했는지 확인하는 함수"""
        # 상대방이 YACHT 규칙을 사용했는지 확인
        if self.opp_state.rule_score[DiceRule.YACHT.value] is not None:
            if self.opp_state.rule_score[DiceRule.YACHT.value] > 0:
                self.opponent_yacht_completed = True

    def check_my_yacht_completion(self):
        """내가 YACHT를 완성했는지 확인하는 함수"""
        # 내가 YACHT 규칙을 사용했는지 확인
        if self.my_state.rule_score[DiceRule.YACHT.value] is not None:
            if self.my_state.rule_score[DiceRule.YACHT.value] > 0:
                self.my_yacht_completed = True

    def should_block_yacht(self, dice_a: List[int], dice_b: List[int]) -> Optional[Tuple[str, int]]:
        """YACHT 방해가 필요한지 확인하는 함수"""
        # 상대방이 이미 YACHT를 완성했다면 방해하지 않음
        if self.opponent_yacht_completed:
            return None
        
        # 상대방이 4개 중복을 가지고 있는지 확인
        opp_dice = self.opp_state.dice
        if len(opp_dice) < 4:
            return None
        
        opp_counts = [0] * 7  # 상대방 주사위 개수
        for dice in opp_dice:
            opp_counts[dice] += 1
        
        # 상대방이 4개 중복을 가지고 있는지 확인
        four_duplicate_number = None
        for i in range(1, 7):
            if opp_counts[i] >= 4:
                four_duplicate_number = i
                break
        
        if four_duplicate_number is not None:
            # A그룹과 B그룹에서 해당 숫자가 몇 개 있는지 확인
            count_a = dice_a.count(four_duplicate_number)
            count_b = dice_b.count(four_duplicate_number)
            
            # 해당 숫자를 얻을 수 있는 그룹이 하나만 있는지 확인
            if (count_a > 0 and count_b == 0) or (count_a == 0 and count_b > 0):
                target_group = "A" if count_a > 0 else "B"
                return (target_group, 5001)
        
        return None

    def get_my_max_duplicate_number(self) -> Optional[Tuple[int, int]]:
        """내가 보유한 주사위에서 가장 많이 중복된 숫자를 찾는 함수"""
        my_dice = self.my_state.dice
        if not my_dice:
            return None
        
        counts = [0] * 7  # 1~6까지의 개수 (인덱스 0은 사용하지 않음)
        for dice in my_dice:
            counts[dice] += 1
        
        # 가장 많이 중복된 숫자와 그 개수 찾기
        max_count = 0
        max_number = 0
        for i in range(1, 7):
            if counts[i] > max_count:
                max_count = counts[i]
                max_number = i
        
        if max_count > 0:
            return (max_number, max_count)
        return None

    def select_group_based_on_my_dice(self, dice_a: List[int], dice_b: List[int]) -> str:
        """내가 보유한 주사위의 중복 패턴을 기반으로 그룹을 선택하는 함수"""
        # 내가 보유한 주사위에서 가장 많이 중복된 숫자 찾기
        my_max_info = self.get_my_max_duplicate_number()
        if my_max_info is not None:
            my_max_number, _ = my_max_info
            # A그룹과 B그룹에서 해당 숫자가 몇 개 있는지 확인
            count_a = dice_a.count(my_max_number)
            count_b = dice_b.count(my_max_number)
            
            # 해당 숫자가 더 많이 있는 그룹 선택
            if count_a > count_b:
                return "A"
            elif count_b > count_a:
                return "B"
            elif count_a == count_b and count_a > 0:
                # 개수가 같다면 턴에 따라 다르게 처리
                if self.current_round <= 8:
                    # 1~8턴: 큰 수를 가져오기
                    sum_a = sum(dice_a)
                    sum_b = sum(dice_b)
                    return "A" if sum_a > sum_b else "B"
                else:
                    # 9턴 이후: 남은 조합에 따라 다르게 처리
                    return self.select_group_by_remaining_combinations(dice_a, dice_b)
        
        # 기본값: 합이 높은 쪽 선택
        sum_a = sum(dice_a)
        sum_b = sum(dice_b)
        return "A" if sum_a > sum_b else "B"

    def select_group_by_remaining_combinations(self, dice_a: List[int], dice_b: List[int]) -> str:
        """남은 조합에 따라 그룹을 선택하는 함수 (9턴 이후)"""
        # 사용하지 않은 규칙들 확인
        unused_rules = [i for i, score in enumerate(self.my_state.rule_score) if score is None]
        
        # 각 그룹에서 사용할 수 있는 조합 점수 계산
        score_a = self.calculate_potential_score(dice_a, unused_rules)
        score_b = self.calculate_potential_score(dice_b, unused_rules)
        
        return "A" if score_a > score_b else "B"

    def calculate_potential_score(self, dice: List[int], unused_rules: List[int]) -> int:
        """주사위 그룹에서 사용할 수 있는 잠재적 점수 계산"""
        max_score = 0
        
        for rule_index in unused_rules:
            rule = DiceRule(rule_index)
            # 각 규칙에 대해 가능한 최고 점수 계산
            score = self.calculate_rule_potential_score(dice, rule)
            max_score = max(max_score, score)
        
        return max_score

    def calculate_rule_potential_score(self, dice: List[int], rule: DiceRule) -> int:
        """특정 규칙에 대한 잠재적 점수 계산"""
        if rule == DiceRule.ONE:
            return sum(d for d in dice if d == 1) * 1000
        elif rule == DiceRule.TWO:
            return sum(d for d in dice if d == 2) * 1000
        elif rule == DiceRule.THREE:
            return sum(d for d in dice if d == 3) * 1000
        elif rule == DiceRule.FOUR:
            return sum(d for d in dice if d == 4) * 1000
        elif rule == DiceRule.FIVE:
            return sum(d for d in dice if d == 5) * 1000
        elif rule == DiceRule.SIX:
            return sum(d for d in dice if d == 6) * 1000
        elif rule == DiceRule.CHOICE:
            return sum(dice) * 1000
        elif rule == DiceRule.FOUR_OF_A_KIND:
            if any(dice.count(i) >= 4 for i in range(1, 7)):
                return sum(dice) * 1000
            return 0
        elif rule == DiceRule.FULL_HOUSE:
            has_pair = any(dice.count(i) == 2 or dice.count(i) == 5 for i in range(1, 7))
            has_triple = any(dice.count(i) == 3 or dice.count(i) == 5 for i in range(1, 7))
            if has_pair and has_triple:
                return sum(dice) * 1000
            return 0
        elif rule == DiceRule.SMALL_STRAIGHT:
            has = [False] * 7
            for d in dice:
                has[d] = True
            if ((has[1] and has[2] and has[3] and has[4]) or
                (has[2] and has[3] and has[4] and has[5]) or
                (has[3] and has[4] and has[5] and has[6])):
                return 15000
            return 0
        elif rule == DiceRule.LARGE_STRAIGHT:
            has = [False] * 7
            for d in dice:
                has[d] = True
            if ((has[1] and has[2] and has[3] and has[4] and has[5]) or
                (has[2] and has[3] and has[4] and has[5] and has[6])):
                return 30000
            return 0
        elif rule == DiceRule.YACHT:
            if any(dice.count(i) == 5 for i in range(1, 7)):
                return 50000
            return 0
        return 0

    def calculate_strategic_bid_amount(self, dice_a: List[int], dice_b: List[int], selected_group: str) -> int:
        """전략적 입찰 금액을 계산하는 함수"""
        selected_dice = dice_a if selected_group == "A" else dice_b
        max_count = self.get_max_duplicate_count(selected_dice)
        
        if self.current_round <= 2:
            # 첫 번째 턴: 중복 개수와 합계를 고려한 전략적 입찰
            dice_sum = sum(selected_dice)
            if max_count == 5:
                return 7999  # YACHT 가능성
            elif max_count == 4:
                return 3001  # FOUR_OF_A_KIND 가능성
            elif max_count == 3:
                return 1001  # FULL_HOUSE 가능성
            elif max_count == 2:
                return 98   # 기본 중복
            else:
                # 중복이 없어도 높은 합계면 입찰
                return 201 if dice_sum >= 20 else 1
        
        elif self.current_round == 3:
            # 세 번째 턴: 중복되는게 3개 이상인지 확인
            if max_count >= 3:
                return 999  # 3개 이상 중복이면 999 입찰
            else:
                return 0    # 3개 이상 중복이 없으면 0 입찰
        
        elif 4 <= self.current_round <= 8:
            # 4~8턴: 중복 수에 따른 전략적 입찰
            if not self.opponent_bids:
                return 0  # 상대방 입찰 기록이 없으면 0
            
            # 내가 YACHT를 완성했다면 0 또는 (최소 입찰 + 1) 중 랜덤 선택
            if self.my_yacht_completed:
                min_opponent_bid = min(self.opponent_bids.values())
                option1 = 0
                option2 = min(9999, max(0, min_opponent_bid + 1))
                
                # 50% 확률로 0 또는 (최소 입찰 + 1) 선택
                return random.choice([option1, option2])
            
            min_opponent_bid = min(self.opponent_bids.values())
            max_opponent_bid = max(self.opponent_bids.values())
            
            # 내가 보유한 주사위와 선택한 그룹의 주사위를 합쳐서 중복 수 계산
            combined_dice = self.my_state.dice + selected_dice
            combined_max_count = self.get_max_duplicate_count(combined_dice)
            
            if combined_max_count == 3:
                # 중복수가 3개인 카드가 나오면 (최소 입찰 + 1) 선택
                return min(9999, max(0, min_opponent_bid + 1))
            elif combined_max_count == 4:
                # 중복수가 4개인 카드가 나오면 (최대 입찰 - 1) 선택 (음수 방지)
                return min(9999, max(0, max_opponent_bid - 1))
            else:
                # 그 외의 경우 0 입찰
                return 0
        
        elif self.current_round >= 9:
            # 9턴부터: 랜덤하게 선택
            if not self.opponent_bids:
                return 0  # 상대방 입찰 기록이 없으면 0
            
            min_opponent_bid = min(self.opponent_bids.values())
            option1 = 0
            option2 = min(9999, max(0, min_opponent_bid + 1))
            
            # 50% 확률로 0 또는 (최소 입찰 + 1) 선택
            return random.choice([option1, option2])
        
        else:
            return 1  # 기본값

    def count_unused_rules(self) -> int:
        """사용하지 않은 규칙의 개수를 반환하는 함수"""
        return sum(1 for score in self.my_state.rule_score if score is None)

    def get_unused_rule_indices(self) -> List[int]:
        """사용하지 않은 규칙의 인덱스들을 반환하는 함수"""
        return [i for i, score in enumerate(self.my_state.rule_score) if score is None]

    def count_critical_rules(self) -> int:
        """중요한 규칙(높은 점수)의 개수를 반환하는 함수"""
        critical_rules = [
            DiceRule.YACHT.value,
            DiceRule.LARGE_STRAIGHT.value,
            DiceRule.SMALL_STRAIGHT.value,
            DiceRule.FOUR_OF_A_KIND.value,
        ]
        
        return sum(1 for rule_index in critical_rules 
                  if self.my_state.rule_score[rule_index] is None)

    def should_use_rule_strategically(self, rule: DiceRule, score: int) -> bool:
        """현재 턴과 상황에 따라 규칙을 전략적으로 사용할지 결정하는 함수"""
        
        # 1. YACHT 규칙: 매우 높은 점수이므로 조건이 맞으면 사용
        if rule == DiceRule.YACHT:
            return score > 0  # YACHT가 가능하면 무조건 사용
        
        # 2. LARGE_STRAIGHT: 높은 점수이므로 조건이 맞으면 사용
        if rule == DiceRule.LARGE_STRAIGHT:
            return score > 0  # LARGE_STRAIGHT가 가능하면 사용
        
        # 3. SMALL_STRAIGHT: 중간 점수이므로 전략적 판단
        if rule == DiceRule.SMALL_STRAIGHT:
            if score > 0:  # 완성된 스트레이트 (15000점)
                return True  # 완성된 스트레이트는 언제든 사용
            else:  # 불완전한 스트레이트 - 초반에만 시도
                return self.current_round <= 6
        
        # 4. FOUR_OF_A_KIND: 높은 점수이므로 조건이 맞으면 사용
        if rule == DiceRule.FOUR_OF_A_KIND:
            return score > 0
        
        # 5. FULL_HOUSE: 중간 점수이므로 전략적 판단
        if rule == DiceRule.FULL_HOUSE:
            if self.current_round <= 6:  # 초반에는 아껴두기
                return score > 0 and self.current_round >= 4
            else:  # 후반에는 사용
                return score > 0
        
        # 6. CHOICE: 10턴 이후에만 고려 (이미 find_optimal_dice_for_rule에서 처리됨)
        if rule == DiceRule.CHOICE:
            return self.current_round >= 10 and score > 0
        
        # 7. 기본 규칙들 (ONE~SIX): 점수에 따라 판단
        if rule in [DiceRule.ONE, DiceRule.TWO, DiceRule.THREE, DiceRule.FOUR, DiceRule.FIVE, DiceRule.SIX]:
            # 높은 점수(3000점 이상)이면 사용
            if score >= 3000:
                return True
            # 중간 점수(1000점 이상)이면 턴에 따라 판단
            elif score >= 1000:
                if self.current_round <= 4:  # 초반에는 아껴두기
                    return False
                else:  # 후반에는 사용
                    return True
            # 낮은 점수는 후반에만 사용
            else:
                return self.current_round >= 8
        
        return True  # 기본적으로는 사용

    # ================================ [필수 구현] ================================
    # ============================================================================
    # 주사위가 주어졌을 때, 어디에 얼마만큼 베팅할지 정하는 함수
    # 입찰할 그룹과 베팅 금액을 pair로 묶어서 반환
    # ============================================================================
    def calculate_bid(self, dice_a: List[int], dice_b: List[int]) -> Bid:
        self.log_time(f"calculate_bid called with dice_a={dice_a}, dice_b={dice_b}")
        
        # 1. YACHT 방해가 필요한지 먼저 확인
        block_result = self.should_block_yacht(dice_a, dice_b)
        if block_result is not None:
            block_group, block_amount = block_result
            self.log_time(f"YACHT block: {block_group} {block_amount}")
            return Bid(block_group, block_amount)
        
        # 2. 중복이 더 많은 그룹 선택
        max_count_a = self.get_max_duplicate_count(dice_a)
        max_count_b = self.get_max_duplicate_count(dice_b)
        group = "A" if max_count_a >= max_count_b else "B"
        
        # 3. 턴별 전략적 입찰 금액 계산
        amount = self.calculate_strategic_bid_amount(dice_a, dice_b, group)
        
        self.log_time(f"Bid calculated: {group} {amount}")
        return Bid(group, amount)

    # ============================================================================
    # 주어진 주사위에 대해 사용할 규칙과 주사위를 정하는 함수
    # 사용할 규칙과 사용할 주사위의 목록을 pair로 묶어서 반환
    # ============================================================================
    def calculate_put(self) -> DicePut:
        self.log_time(f"calculate_put called with dice={self.my_state.dice}")
        
        # 정렬된 주사위를 한 번만 계산하여 저장 (중복 제거된 버전과 일반 버전)
        self.sorted_dice_unique = sorted(set(self.my_state.dice))
        self.sorted_dice = sorted(self.my_state.dice, reverse=True)
        
        # 사용하지 않은 규칙들 찾기
        unused_rules = [i for i, score in enumerate(self.my_state.rule_score) if score is None]
        
        best_rule = None
        best_dice = None
        best_score = -1
        
        # 전략적 규칙 우선순위: 높은 점수 규칙을 우선적으로 고려
        priority_rules = [
            DiceRule.YACHT.value,           # 50000점
            DiceRule.LARGE_STRAIGHT.value,  # 30000점
            DiceRule.SMALL_STRAIGHT.value,  # 15000점
            DiceRule.FOUR_OF_A_KIND.value,  # 높은 점수
            DiceRule.FULL_HOUSE.value,      # 높은 점수
            DiceRule.CHOICE.value,          # 높은 점수
            DiceRule.SIX.value,             # 기본 규칙 (높은 숫자)
            DiceRule.FIVE.value,
            DiceRule.FOUR.value,
            DiceRule.THREE.value,
            DiceRule.TWO.value,
            DiceRule.ONE.value,             # 기본 규칙 (낮은 숫자)
        ]
        
        # 고점수 특수 규칙 완성 후 낮은 숫자 정리 전략
        high_value_rules_completed = (
            self.my_yacht_completed and 
            self.my_state.rule_score[DiceRule.LARGE_STRAIGHT.value] is not None and
            self.my_state.rule_score[DiceRule.SMALL_STRAIGHT.value] is not None
        )
        
        if high_value_rules_completed:
            # 1,2,3이 3개 이상 있으면 우선적으로 정리 (점수 무시)
            for low_num in [1, 2, 3]:
                count = self.my_state.dice.count(low_num)
                if count >= 3:  # 3개 이상이면 정리 대상
                    rule_index = low_num - 1  # 1→0(ONE), 2→1(TWO), 3→2(THREE)
                    if rule_index in unused_rules:
                        rule = DiceRule(rule_index)
                        dice, score = self.find_optimal_dice_for_rule(rule)
                        
                        self.log_time(f"High-value rules completed - prioritizing cleanup of {count} dice of value {low_num}")
                        return DicePut(rule, dice)
        
        elif self.my_yacht_completed:
            # YACHT만 완성된 경우: 4개 이상의 낮은 숫자만 정리
            for low_num in [1, 2, 3]:
                count = self.my_state.dice.count(low_num)
                if count >= 4:
                    rule_index = low_num - 1  # 1→0(ONE), 2→1(TWO), 3→2(THREE)
                    if rule_index in unused_rules:
                        rule = DiceRule(rule_index)
                        dice, score = self.find_optimal_dice_for_rule(rule)
                        
                        self.log_time(f"YACHT completed - cleaning up {count} dice of value {low_num}")
                        return DicePut(rule, dice)
        
        # 우선순위에 따라 규칙 검사
        for priority_rule in priority_rules:
            if priority_rule in unused_rules:
                rule = DiceRule(priority_rule)
                dice, score = self.find_optimal_dice_for_rule(rule)
                
                # 현재 턴과 규칙에 따른 전략적 선택
                if self.should_use_rule_strategically(rule, score):
                    self.log_time(f"Strategic rule considered: {rule.name}, score: {score}, current best: {best_rule.name if best_rule else None} ({best_score})")
                    
                    # 불완전한 스트레이트의 경우 우선순위를 고려한 특별 처리
                    if rule in [DiceRule.SMALL_STRAIGHT, DiceRule.LARGE_STRAIGHT] and score == 0:
                        # 불완전한 스트레이트는 우선순위가 높으므로 기존 선택을 덮어씀
                        # 단, 이미 완성된 고점수 규칙(YACHT, 완성된 스트레이트)이 있다면 제외
                        if (best_rule is None or 
                            (best_rule not in [DiceRule.YACHT, DiceRule.LARGE_STRAIGHT, DiceRule.SMALL_STRAIGHT] or best_score == 0)):
                            self.log_time(f"Selecting incomplete straight: {rule.name}")
                            best_score = score
                            best_rule = rule
                            best_dice = dice
                    elif score > best_score:
                        self.log_time(f"Selecting higher score rule: {rule.name} ({score} > {best_score})")
                        best_score = score
                        best_rule = rule
                        best_dice = dice
                else:
                    self.log_time(f"Strategic rule rejected: {rule.name}, score: {score}")
        
        # 전략적 선택이 없으면 모든 규칙을 점수 기반으로 검사
        if best_rule is None:
            for rule_index in unused_rules:
                rule = DiceRule(rule_index)
                dice, score = self.find_optimal_dice_for_rule(rule)
                
                if score > best_score:
                    best_score = score
                    best_rule = rule
                    best_dice = dice
        
        # 최적의 조합이 없으면 기본값 사용
        if best_rule is None:
            best_rule = DiceRule(unused_rules[0])
            best_dice = self.my_state.dice[:5] if len(self.my_state.dice) >= 5 else [0] * 5
        
        self.log_time(f"Put calculated: {best_rule.name} {best_dice} (score: {best_score})")
        return DicePut(best_rule, best_dice)

    def calculate_simple_put(self) -> DicePut:
        """11번째 턴 이후의 간단한 조합 계산 (시간 최적화)"""
        unused_rules = [i for i, score in enumerate(self.my_state.rule_score) if score is None]
        
        # 가장 간단한 방법: 첫 번째 사용하지 않은 규칙과 처음 5개 주사위 사용
        rule_index = unused_rules[0] if unused_rules else 0
        dice = self.my_state.dice[:5] if len(self.my_state.dice) >= 5 else [0] * 5
        
        return DicePut(DiceRule(rule_index), dice)

    def calculate_13th_round_put(self) -> DicePut:
        """13번째 턴에서 남은 주사위 5개를 남은 규칙에 넣기"""
        my_dice = self.my_state.dice
        
        # 사용하지 않은 규칙들 찾기
        unused_rules = [i for i, score in enumerate(self.my_state.rule_score) if score is None]
        
        # 남은 주사위 5개를 그대로 사용
        dice = my_dice[:5] if len(my_dice) >= 5 else [0] * 5
        
        # 남은 규칙 중 첫 번째 규칙 사용
        rule_index = unused_rules[0] if unused_rules else 0
        
        return DicePut(DiceRule(rule_index), dice)

    def find_optimal_dice_for_rule(self, rule: DiceRule) -> Tuple[List[int], int]:
        """규칙별 최적 주사위 조합 찾기"""
        my_dice = self.my_state.dice.copy()  # 복사본 사용
        
        # 기본 규칙들 (ONE~SIX): 해당 숫자를 최대한 많이 선택
        if rule in [DiceRule.ONE, DiceRule.TWO, DiceRule.THREE, DiceRule.FOUR, DiceRule.FIVE, DiceRule.SIX]:
            target_number = rule.value + 1  # ONE=0이므로 +1 (ONE→1, TWO→2, ..., SIX→6)
            target_count = my_dice.count(target_number)  # 정렬된 주사위 불필요, count 사용
            
            if target_count > 0:
                # 해당 숫자를 최대한 많이 선택 (최대 5개)
                dice = []
                temp_dice = my_dice.copy()
                
                # 해당 숫자들을 우선 선택
                for _ in range(min(5, target_count)):
                    dice.append(target_number)
                    temp_dice.remove(target_number)
                
                # 5개가 안 되면 나머지 주사위로 채움 (특별한 우선순위 적용)
                remaining_count = {}
                for d in temp_dice:
                    remaining_count[d] = remaining_count.get(d, 0) + 1
                
                # FOUR_OF_A_KIND, FULL_HOUSE가 아직 사용 가능한지 확인
                four_of_kind_available = self.my_state.rule_score[DiceRule.FOUR_OF_A_KIND.value] is None
                full_house_available = self.my_state.rule_score[DiceRule.FULL_HOUSE.value] is None
                high_rules_available = four_of_kind_available or full_house_available
                
                # 1순위: FOUR_OF_A_KIND나 FULL_HOUSE가 사용 가능하면 6을 최우선
                if high_rules_available and 6 in temp_dice:
                    while len(dice) < 5 and 6 in temp_dice:
                        dice.append(6)
                        temp_dice.remove(6)
                
                # 2순위: 중복이 없는 수들을 가장 작은 수부터 선택
                unique_dice = [num for num, count in remaining_count.items() if count == 1 and num in temp_dice]
                unique_dice.sort()  # 작은 수부터 정렬
                
                while len(dice) < 5 and unique_dice:
                    selected = unique_dice.pop(0)
                    if selected in temp_dice:  # 아직 남아있는지 확인
                        dice.append(selected)
                        temp_dice.remove(selected)
                
                # 3순위: 나머지 주사위로 채움
                # 고점수 규칙들이 달성된 경우 작은 숫자부터 선택 (큰 숫자 보존)
                large_straight_completed = self.my_state.rule_score[DiceRule.LARGE_STRAIGHT.value] is not None
                small_straight_completed = self.my_state.rule_score[DiceRule.SMALL_STRAIGHT.value] is not None
                # LARGE_STRAIGHT, SMALL_STRAIGHT 둘 다 달성되면 6 보존
                straights_completed = large_straight_completed and small_straight_completed
                
                if straights_completed:
                    # 고점수 규칙 달성 시: 작은 숫자부터 선택 (큰 숫자 보존)
                    temp_dice.sort()  # 작은 숫자부터 정렬
                    while len(dice) < 5 and temp_dice:
                        dice.append(temp_dice.pop(0))  # 가장 작은 숫자부터 선택
                else:
                    # 기존 로직: 임의 순서
                    while len(dice) < 5 and temp_dice:
                        dice.append(temp_dice.pop(0))
                
                # 여전히 5개가 안 되면 0으로 채움
                while len(dice) < 5:
                    dice.append(0)
                
                score = self.calculate_rule_potential_score(dice, rule)
                return (dice, score)
        
        elif rule == DiceRule.CHOICE:
            # 10턴 이후에만 CHOICE 고려
            if self.current_round >= 10:
                # 가장 높은 숫자 5개 선택
                dice = self.sorted_dice[:5]
                score = self.calculate_rule_potential_score(dice, rule)
                return (dice, score)
            else:
                # 10턴 이전에는 CHOICE를 0점으로 처리
                return ([0] * 5, 0)
        
        elif rule == DiceRule.FOUR_OF_A_KIND:
            # 8라운드 전까지는 4,5,6으로만 구성된 경우에만 사용
            if self.current_round <= 8:
                # 8라운드 전: 4,5,6으로만 구성된 경우만 허용
                for num in range(4, 7):
                    count = my_dice.count(num)
                    if count >= 4:
                        # 실제 보유한 해당 숫자들을 사용
                        target_dice = []
                        temp_dice = my_dice.copy()
                        
                        # 해당 숫자 4개 사용
                        for i in range(4):
                            target_dice.append(num)
                            temp_dice.remove(num)
                        
                        # 나머지 1개는 다른 주사위 중에서 선택
                        if temp_dice:
                            target_dice.append(temp_dice[0])
                        else:
                            target_dice.append(num)  # 기본값
                        
                        score = self.calculate_rule_potential_score(target_dice, rule)
                        return (target_dice, score)
                
                # 8라운드 전에 4,5,6으로 조건 만족하지 않으면 0점
                return ([0] * 5, 0)
            
            else:
                # 8라운드 이후: 모든 숫자 허용
                for num in range(1, 7):
                    count = my_dice.count(num)
                    if count >= 4:
                        # 실제 보유한 해당 숫자들을 사용
                        target_dice = []
                        temp_dice = my_dice.copy()
                        
                        # 해당 숫자 4개 사용
                        for i in range(4):
                            target_dice.append(num)
                            temp_dice.remove(num)
                        
                        # 나머지 1개는 다른 주사위 중에서 선택
                        if temp_dice:
                            target_dice.append(temp_dice[0])
                        else:
                            target_dice.append(num)  # 기본값
                        
                        score = self.calculate_rule_potential_score(target_dice, rule)
                        return (target_dice, score)
        
        elif rule == DiceRule.FULL_HOUSE:
            # 8라운드 전까지는 4,5,6으로만 구성된 경우에만 사용
            if self.current_round <= 8:
                # 8라운드 전: 4,5,6으로만 구성된 경우만 허용
                for num1 in range(4, 7):
                    count1 = my_dice.count(num1)
                    if count1 >= 3:
                        for num2 in range(4, 7):
                            if num2 != num1:
                                count2 = my_dice.count(num2)
                                if count2 >= 2:
                                    # 실제 보유한 주사위들로 조합 생성
                                    target_dice = []
                                    temp_dice = my_dice.copy()
                                    
                                    # 첫 번째 숫자 3개 사용
                                    for i in range(3):
                                        target_dice.append(num1)
                                        temp_dice.remove(num1)
                                    
                                    # 두 번째 숫자 2개 사용
                                    for i in range(2):
                                        target_dice.append(num2)
                                        temp_dice.remove(num2)
                                    
                                    score = self.calculate_rule_potential_score(target_dice, rule)
                                    return (target_dice, score)
                
                # 8라운드 전에 4,5,6으로 조건 만족하지 않으면 0점
                return ([0] * 5, 0)
            
            else:
                # 8라운드 이후: 모든 숫자 허용
                for num1 in range(1, 7):
                    count1 = my_dice.count(num1)
                    if count1 >= 3:
                        for num2 in range(1, 7):
                            if num2 != num1:
                                count2 = my_dice.count(num2)
                                if count2 >= 2:
                                    # 실제 보유한 주사위들로 조합 생성
                                    target_dice = []
                                    temp_dice = my_dice.copy()
                                    
                                    # 첫 번째 숫자 3개 사용
                                    for i in range(3):
                                        target_dice.append(num1)
                                        temp_dice.remove(num1)
                                    
                                    # 두 번째 숫자 2개 사용
                                    for i in range(2):
                                        target_dice.append(num2)
                                        temp_dice.remove(num2)
                                    
                                    score = self.calculate_rule_potential_score(target_dice, rule)
                                    return (target_dice, score)
        
        elif rule == DiceRule.SMALL_STRAIGHT:
            # 1234, 2345, 3456 중 하나 찾기
            sorted_dice = self.sorted_dice_unique
            
            # 완성된 스트레이트 확인
            sequences = [[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]]
            
            for sequence in sequences:
                if all(x in sorted_dice for x in sequence):
                    # 완성된 스트레이트가 있으면 해당 숫자들만 선택
                    target_dice = []
                    temp_dice = my_dice.copy()
                    
                    for num in sequence:
                        if num in temp_dice:
                            target_dice.append(num)
                            temp_dice.remove(num)
                    
                    # 5번째는 남은 주사위 중에서 선택 (완성된 스트레이트인 경우만)
                    if temp_dice:
                        target_dice.append(temp_dice[0])
                    else:
                        target_dice.append(sequence[-1] + 1 if sequence[-1] < 6 else sequence[0] - 1)
                    
                    score = self.calculate_rule_potential_score(target_dice, rule)
                    return (target_dice, score)
            
            # 완성된 스트레이트가 없으면 가장 유력한 불완전 스트레이트 찾기
            best_partial = None
            best_count = 0
            
            for sequence in sequences:
                count = sum(1 for x in sequence if x in sorted_dice)
                if count > best_count:
                    best_count = count
                    best_partial = sequence
            
            # 불완전한 스트레이트가 있으면 해당 숫자들만 유지
            if best_partial and best_count >= 1:
                target_dice = []
                temp_dice = my_dice.copy()
                
                for num in best_partial:
                    if num in temp_dice:
                        target_dice.append(num)
                        temp_dice.remove(num)
                
                # 5개를 맞추기 위해 무작위 주사위 추가하지 않음
                # 필요한 숫자만 유지하여 다음 턴에서 완성 기회를 높임
                score = 0  # 불완전한 스트레이트는 0점
                return (target_dice, score)
            
        elif rule == DiceRule.LARGE_STRAIGHT:
            # 12345 또는 23456 찾기
            sorted_dice = self.sorted_dice_unique
            
            # 12345 찾기
            if all(x in sorted_dice for x in [1, 2, 3, 4, 5]):
                target_dice = []
                temp_dice = my_dice.copy()
                
                for num in [1, 2, 3, 4, 5]:
                    if num in temp_dice:
                        target_dice.append(num)
                        temp_dice.remove(num)
                
                score = self.calculate_rule_potential_score(target_dice, rule)
                return (target_dice, score)
            
            # 23456 찾기
            elif all(x in sorted_dice for x in [2, 3, 4, 5, 6]):
                target_dice = []
                temp_dice = my_dice.copy()
                
                for num in [2, 3, 4, 5, 6]:
                    if num in temp_dice:
                        target_dice.append(num)
                        temp_dice.remove(num)
                
                score = self.calculate_rule_potential_score(target_dice, rule)
                return (target_dice, score)
        
        elif rule == DiceRule.YACHT:
            # 5개 모두 같은 숫자 찾기
            for num in range(1, 7):
                count = my_dice.count(num)
                if count >= 5:
                    # 실제 보유한 해당 숫자들 중 5개 선택
                    target_dice = []
                    temp_dice = my_dice.copy()
                    
                    for i in range(5):
                        target_dice.append(num)
                        temp_dice.remove(num)
                    
                    score = self.calculate_rule_potential_score(target_dice, rule)
                    return (target_dice, score)
        
        # 규칙에 맞는 조합을 찾지 못한 경우, 기본 조합 사용
        dice = my_dice[:5] if len(my_dice) >= 5 else [0] * 5
        score = self.calculate_rule_potential_score(dice, rule)
        return (dice, score)

    # ============================== [필수 구현 끝] ==============================

    def update_get(
        self,
        dice_a: List[int],
        dice_b: List[int],
        my_bid: Bid,
        opp_bid: Bid,
        my_group: str,
    ):
        """입찰 결과를 받아서 상태 업데이트"""
        self.log_time(f"update_get: my_group={my_group}, my_bid={my_bid}, opp_bid={opp_bid}")
        
        # 상대방의 입찰 가격 저장
        self.save_opponent_bid(self.current_round, opp_bid.amount)
        
        # 그룹에 따라 주사위 분배
        if my_group == "A":
            self.my_state.add_dice(dice_a)
            self.opp_state.add_dice(dice_b)
        else:
            self.my_state.add_dice(dice_b)
            self.opp_state.add_dice(dice_a)

        # 입찰 결과에 따른 점수 반영
        my_bid_ok = my_bid.group == my_group
        self.my_state.bid(my_bid_ok, my_bid.amount)

        opp_group = "B" if my_group == "A" else "A"
        opp_bid_ok = opp_bid.group == opp_group
        self.opp_state.bid(opp_bid_ok, opp_bid.amount)
        
        self.log_time(f"After update_get: my_dice={self.my_state.dice}, opp_dice={self.opp_state.dice}")

    def update_put(self, put: DicePut):
        """내가 주사위를 배치한 결과 반영"""
        self.log_time(f"update_put: {put.rule.name} {put.dice}")
        self.my_state.use_dice(put)
        # 내가 YACHT를 완성했는지 확인
        self.check_my_yacht_completion()
        self.log_time(f"After update_put: remaining_dice={self.my_state.dice}")

    def update_set(self, put: DicePut):
        """상대가 주사위를 배치한 결과 반영"""
        self.log_time(f"update_set: {put.rule.name} {put.dice}")
        self.opp_state.use_dice(put)
        # 상대방이 YACHT를 완성했는지 확인
        self.check_opponent_yacht_completion()


def main():
    game = Game()

    # 입찰 라운드에서 나온 주사위들
    dice_a, dice_b = [0] * 5, [0] * 5
    # 내가 마지막으로 한 입찰 정보
    my_bid = Bid("", 0)

    while True:
        try:
            line = input().strip()
            if not line:
                continue

            command, *args = line.split()
            game.log_time(f"Received command: {command} {args}")

            if command == "READY":
                # 게임 시작
                game.log_time("Sending OK")
                print("OK")
                continue

            if command == "ROLL":
                # 주사위 굴리기 결과 받기
                game.current_round += 1  # 턴 증가
                str_a, str_b = args
                for i, c in enumerate(str_a):
                    dice_a[i] = int(c)  # 문자를 숫자로 변환
                for i, c in enumerate(str_b):
                    dice_b[i] = int(c)  # 문자를 숫자로 변환
                
                game.log_time(f"ROLL: dice_a={dice_a}, dice_b={dice_b}, round={game.current_round}")
                my_bid = game.calculate_bid(dice_a, dice_b)
                game.log_time(f"Sending BID: {my_bid.group} {my_bid.amount}")
                print(f"BID {my_bid.group} {my_bid.amount}")
                continue

            if command == "GET":
                # 주사위 받기
                get_group, opp_group, opp_score = args
                opp_score = int(opp_score)
                game.log_time(f"GET: get_group={get_group}, opp_group={opp_group}, opp_score={opp_score}")
                game.update_get(
                    dice_a, dice_b, my_bid, Bid(opp_group, opp_score), get_group
                )
                continue

            if command == "SCORE":
                # 주사위 골라서 배치하기
                game.log_time("SCORE command received")
                put = game.calculate_put()
                game.update_put(put)
                assert put.rule is not None
                game.log_time(f"Sending PUT: {put.rule.name} {''.join(map(str, put.dice))}")
                print(f"PUT {put.rule.name} {''.join(map(str, put.dice))}")
                continue

            if command == "SET":
                # 상대의 주사위 배치
                rule, str_dice = args
                dice = [int(c) for c in str_dice]
                game.log_time(f"SET: {rule} {dice}")
                game.update_set(DicePut(DiceRule[rule], dice))
                continue

            if command == "FINISH":
                # 게임 종료
                game.log_time("FINISH command received")
                break

            # 알 수 없는 명령어 처리
            game.log_time(f"Invalid command: {command}")
            print(f"Invalid command: {command}", file=sys.stderr)
            sys.exit(1)

        except EOFError:
            game.log_time("EOFError occurred")
            break
        except Exception as e:
            game.log_time(f"Exception occurred: {e}")
            print(f"# Debug: Exception: {e}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
